import asyncio
import json
import logging
import sys
import random
import aioredis
import time
from aiohttp import ClientSession, WSMsgType, TCPConnector
import aiohttp
import uvloop
import redis
from .systeminfo import CPU_loading_info, Memory_info, Loadaverage_info, Disk_info, CPU_number,CPU_Hz
from .utils import RedisKeyWrapper, URLWrapper
from .utils import get_key_tail as gktail
from .utils import wrap_bytes_headers as wrapbh
from .utils import get_ip
from .utils import ws_send_json
from .logger import get_logger

if sys.version_info < (3, 5):
    raise Exception("must use python 3.5 or greater")

# Use uvloop as default
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class BaseAsyncClient(object):
    def __init__(self, id,
                 entrance_urls=[],
                 ip=None,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=5,
                 redis_maxsize=10,
                 ping_entrance_freq=5,
                 log_level=logging.DEBUG, **kwargs):
        self.id = id
        self.ip = ip
        self._loop = loop if loop else asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue_set = {}
        # We use set to maintain unique entrance urls
        self.entrance_urls = set(entrance_urls)
        self._entrance_ws = dict()
        self._connect_entrance_tasks = dict()
        self._peers_ws = dict()
        self._rk = RedisKeyWrapper(self.id)
        self.conf = {
            "ping_entrance_freq": ping_entrance_freq,
            "redis_address": redis_address,
            "redis_db": redis_db,
            "redis_minsize": redis_minsize,
            "redis_maxsize": redis_maxsize
        }
        self.logger = get_logger("AsyncClient", level=log_level)

    @property
    def redis_pool(self):
        return self.rdp

    async def setup_aioredis(self):
        self.rdp = await aioredis.create_pool(self.conf["redis_address"],
                                              db=self.conf["redis_db"],
                                              minsize=self.conf["redis_minsize"],
                                              maxsize=self.conf["redis_minsize"],
                                              encoding="utf-8")

    def start(self):
        """Start process individually, otherwise register on server process"""
        self._loop.run_until_complete(self.setup_aioredis())
        run_task = asyncio.ensure_future(self.run())
        try:
            self.logger.info("{0} Async Client Loop Start...".format(self.id))
            self._loop.run_forever()
        except KeyboardInterrupt:
            run_task.cancel()
            self._loop.run_until_complete(run_task)
        finally:
            self._loop.run_until_complete(self.cleanup())
            self._loop.close()
            self.logger.info("{0} Async Client Loop Stop!".format(self.id))

    async def run(self):
        """Override this method
        Must contain self.session = ClientSession()
        """
        raise NotImplementedError

    async def ping_entrances(self):
        pass

    async def connect_entrance(self, url):
        """
        Handle an websocket between one entrance server, read message and dispatch it.
        After the websocket is closed, remove ws from _entrance_ws dict
        :param url: entrance url
        """
        try:
            async with self.session.ws_connect(url) as ws:
                self.logger.info("Connect to %s " % url)
                self._entrance_ws[url] = ws
                await self.send_entrance(ws)
                await self.process_received_message(ws, url, once=True)
        except (aiohttp.WSServerHandshakeError, aiohttp.ClientOSError):
            self.logger.exception("Unable to connect to %s." % url, exc_info=False)
        except asyncio.CancelledError:
            return
        except:
            self.logger.exception("Fail in connect_entrance.")
        finally:
            self._entrance_ws.pop(url, None)
            self._connect_entrance_tasks.pop(url, None)

    async def send_entrance(self, ws):
        raise NotImplementedError

    async def _dispatch(self, msg, ws):
        try:
            load = msg.json()
            try:
                command = load['COMMAND']
                await getattr(self, "on_" + command, "on_DEFAULT")(load, ws)
            except KeyError:
                self.logger.exception("No COMMAND key in msg.")
                await self.on_DEFAULT(load, ws)
        except ValueError:
            self.logger.exception("Message is not valid JSON.")

    async def process_received_message(self, ws, url, once=False):
        async for msg in ws:
            self.logger.debug("RECEIVE MSG %s, FROM URL: %s." % (str(msg), url))
            if msg.type == WSMsgType.TEXT:
                breakable = await self._dispatch(msg, ws)
                if once or breakable:
                    await ws.close()
                    break
            elif msg.type == WSMsgType.CLOSED:
                break
            elif msg.type == WSMsgType.ERROR:
                break
            else:
                break

    async def on_DEFAULT(self, msg, ws):
        pass

    async def ws_send(self, request, ws):
        """
        :param request: dict
        """
        await ws_send_json(request, ws, self.logger)

    async def cleanup(self):
        """ Called when the loop stop """
        self.logger.info("Cleaning up entrance websockets...")
        self.rdp.close()
        await self.rdp.wait_closed()
        if hasattr(self, "session"):
            self.session.close()
        for ws in self._entrance_ws.keys():
            await self._entrance_ws[ws].close()
        tasks = self._connect_entrance_tasks.values()
        for task in tasks:
            task.cancel()
            await task


class BoxAsyncClient(BaseAsyncClient):

    def __init__(self, id, port,
                 entrance_urls=[],
                 ip=None,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=5,
                 redis_maxsize=10,
                 ping_entrance_freq=10,
                 proxy_port=None,
                 log_level=logging.DEBUG, **kwargs):
        """
        :param port: Where Box server is listening to
        :param ip: Set ip to None if it is not static
        :param proxy_port: We assume that proxy server is used. This should be configured properly,
                           since others will access this box through this port.
        """
        if "box-" not in id:
            self.logger.warning("ID does not contain box-")
            raise ValueError
        super().__init__(id, entrance_urls,
                         ip=ip,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         ping_entrance_freq=ping_entrance_freq)
        self.logger = get_logger("Box-Client", level=log_level)
        self.port = port
        self.proxy_port = self.conf["proxy_port"] = proxy_port

    async def run(self):
        """
        The main job of box client is to ping entrance server, so that others can connect
        to this box.

        :return:
        """
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self.session = ClientSession(connector=conn)
        while True:
            try:
                await self.update_self_exchange()
                await self.ping_entrances()
                await asyncio.sleep(self.conf["ping_entrance_freq"])
            except asyncio.CancelledError:
                break

    async def ping_entrances(self):
        for url in self.entrance_urls:
            if url and url not in self._entrance_ws.keys():
                task = asyncio.ensure_future(self.connect_entrance(url))
                self._connect_entrance_tasks[url] = task
        # Clear set after pinging it
        self.entrance_urls = set()

    async def on_EXCHANGE(self, msg, ws):
        """
        Receive EXCHANGE from entrance server
        """
        try:
            if msg["MESSAGE"] == "ACCEPTED":
                if "ENTRANCE_URLS" in msg:
                    self.entrance_urls.update(msg["ENTRANCE_URLS"])
        except KeyError:
            self.logger.exception("Wrong EXCHANGE format from entrance or error occurs.")
        except:
            pass

    async def send_entrance(self, ws):
        self_exchange = await self.prepare_exchange_data()
        await self.ws_send(self_exchange, ws)
        self.logger.info("SEND Msg to ENTRANCE : %s" % str(self_exchange))

    async def prepare_exchange_data(self):
        with await self.rdp as rdb:
            self_exchange = await rdb.hgetall(self._rk("SELF_EXCHANGE"))
            logs_keys = await rdb.keys(self._rk("TRAFFIC_FLOW")+"*")
            for key in logs_keys:
                log = await rdb.hgetall(key)
                self_exchange[key] = log
        return self_exchange

    async def update_self_exchange(self):
        """ Update Own Exchange Info """
        ip = await get_ip()
        if ip is None:
            raise ValueError("No available sites to get box's ip")
        connect_url = URLWrapper("https://"+ip+":"+str(self.conf["proxy_port"])+"/")("dandelion", self.id, "ws")
        CPU = CPU_loading_info()
        Load = Loadaverage_info()
        Memory = Memory_info()
        Disk = Disk_info()
        ex_dict = {"ID"            : self.id,
                   "IP"            : ip,
                   "PORT"          : self.port if not self.conf["proxy_port"] else self.conf["proxy_port"],
                   "TYPE"          : "BOX",
                   "COMMAND"       : "EXCHANGE",
                   "CONNECT_WS"    : connect_url,
                   "CPU-HZ"        : '{0}'.format(CPU_Hz()),
                   "CPU-NUM"       : '{0}'.format(CPU_number()),
                   "CPU-USR"       : CPU[0],
                   "CPU-SYS"       : CPU[1],
                   "CPU-NIC"       : CPU[2],
                   "CPU-IDLE"      : CPU[3],
                   "CPU-IO"        : CPU[4],
                   "CPU-IRQ"       : CPU[5],
                   "CPU-SIRQ"      : CPU[6],
                   "LOADAVG-1"     : Load[0],
                   "LOADAVG-5"     : Load[1],
                   "LOADAVG-15"    : Load[2],
                   "MEM-TOTAL"     : Memory[0],
                   "MEM-AVAIL"     : Memory[2],
                   "DISK-TOTAL"    : Disk[0],
                   "DISK-AVAIL"    : Disk[1]
                   }
        with await self.rdp as rdb:
            await rdb.hmset_dict(self._rk("SELF_EXCHANGE"), ex_dict)
        self.logger.debug("UPDATE SELF EXCHANGE %s" % str(ex_dict))

    async def peer_connect(self, url, type):
        """ This method is designed to connect box and box so that boxes can communicate
            even if entrance server is down
        """
        pass


class PublisherAsyncClient(BaseAsyncClient):
    def __init__(self, id,
                 entrance_urls=[],
                 ip=None,
                 min_http_peers=10,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=5,
                 redis_maxsize=10,
                 ping_entrance_freq=3,
                 log_level=logging.DEBUG, **kwargs):
        if "publisher-" not in id:
            self.logger.warning("ID does not contain publisher-")
            raise ValueError
        super().__init__(id,
                         entrance_urls=[],
                         ip=ip,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         ping_entrance_freq=ping_entrance_freq,
                         log_level=log_level, **kwargs)

        self.logger = get_logger("Publisher", level=log_level)
        self.min_peers = min_http_peers
        self.current_peers = 0
        self._peers_ws = dict()  # keys: box id; values (dict): url and ws
        self._connect_box_tasks = dict()

    async def run(self):
        if self.ip is None:
            self.ip = await get_ip()
        conn = aiohttp.TCPConnector(verify_ssl=False)
        self.session = ClientSession(connector=conn)
        collect_task = asyncio.ensure_future(self.collecting())
        publish_task = asyncio.ensure_future(self.publish())
        while True:
            try:
                await self.maintain_peers()
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                collect_task.cancel()
                publish_task.cancel()
                await collect_task
                await publish_task
                break

    async def collecting(self):
        """
        Connecting to available entrance servers to collect available boxes.
        """
        while True:
            try:
                for url in self.entrance_urls:
                    if url not in self._entrance_ws.keys():
                        # Create key first, in case that duplicate socket has created
                        self._entrance_ws[url] = None
                        task = asyncio.ensure_future(self.connect_entrance(url))
                        self._connect_entrance_tasks[url] = task
                await asyncio.sleep(self.conf["ping_entrance_freq"])
            except asyncio.CancelledError:
                break

    async def send_entrance(self, ws):
        """
        COMMAND: SEARCH
        """
        request = {
            "ID": self.id,
            "IP": self.ip,
            "TYPE": "PUBLISHER",
            "COMMAND": "SEARCH",
        }
        await self.ws_send(request, ws)

    async def on_SEARCH(self, msg, ws):
        with await self.rdp as rdb:
            if len(msg["BOX_SET"]):
                try:
                    for box_id in msg["BOX_SET"].keys():
                        await rdb.hmset_dict(self._rk("SEARCH", box_id),
                                             msg["BOX_SET"][box_id])
                except KeyError:
                    self.logger.exception("Key failure.")

    async def on_PUBLISH(self, msg, ws):
        # Check that box is accepted to receive publisher's files, otherwise disconnect
        if msg["COMMAND"] == "PUBLISH" and\
           msg["MESSAGE"] == "ACCEPTED":
            return False
        else:
            return True

    async def maintain_peers(self):
        """
        - First rank all known boxes in redis, the algorithm is implemented at rank_boxes
        - According to the ranking, pick boxes with higher scores and then make connection
        - If box's ip or address has changed, then close it
        """
        if len(self._peers_ws) > self.min_peers:
            return
        await self._loop.run_in_executor(None, self.rank_boxes)
        self.logger.info("---Maintain_Peers---")
        with await self.rdp as rdb:
            box_list = await rdb.zrevrangebyscore(self._rk("BOX_RANKING"),
                                                  offset=0,
                                                  count=self.min_peers)
            _peers_ws_keys = list(self._peers_ws)
            for box_id in box_list:
                if box_id not in _peers_ws_keys:
                    self._peers_ws[box_id] = {}
                    self._connect_box_tasks[box_id] = asyncio.ensure_future(self.connect_box(box_id))
            # If box's IP changes after making connection, then remove it.
            for box_id in _peers_ws_keys:
                current_url = (await rdb.hmget(self._rk("SEARCH", box_id), "CONNECT_WS"))[0]
                if not self._peers_ws[box_id].get("url") == current_url:
                    try:
                        await self._peers_ws[box_id]['ws'].close()
                        self._peers_ws.pop(box_id, None)
                        await rdb.zrem(self._rk("BOX_RANKING"), box_id)
                    except:
                        pass

    def rank_boxes(self):
        """
        According to boxes info , rank boxes into a sorted set
        For now, just make every box with score 0
        """
        rdb = redis.StrictRedis(host=self.conf["redis_address"][0],
                                port=self.conf["redis_address"][1],
                                db=self.conf["redis_db"],
                                encoding="utf-8",
                                decode_responses=True)
        boxes = rdb.keys(self._rk("SEARCH", "box*"))
        for box in boxes:
            box = gktail(box)
            rdb.zadd(self._rk("BOX_RANKING"), 0, box)

    async def create_publish_message(self):
        return {
            "ID": self.id,
            "IP": self.ip,
            "TYPE": "PUBLISHER",
            "COMMAND": "PUBLISH"
        }

    async def send_box(self, ws):
        message = await self.create_publish_message()
        await self.ws_send(message, ws)

    async def connect_box(self, box_id):
        with await self.rdp as rdb:
            url = (await rdb.hmget(self._rk("SEARCH", box_id), "CONNECT_WS"))[0]
        try:
            if url is None:
                raise ValueError("No available URL.")
            async with self.session.ws_connect(url) as ws:
                await self.send_box(ws)
                self._peers_ws[box_id] = {
                    'ws': ws,
                    'url': url,
                }
                self.logger.info("Connect to box %s" % box_id)
                await self.process_received_message(ws, url)
        except (aiohttp.WSServerHandshakeError, aiohttp.ClientOSError):
            self.logger.exception("Unable to connect to %s." % url, exc_info=False)
        except asyncio.CancelledError:
            pass
        except:
            self.logger.exception("Fail in connect_box %s" % box_id, exc_info=False)
        finally:
            self._peers_ws.pop(box_id, None)
            with await self.rdp as rdb:
                await rdb.zrem(self._rk("BOX_RANKING"), box_id)
            self._connect_box_tasks.pop(box_id, None)

    async def publish(self):
        """
        1. Select a box to send to.
        2. Read the file
        3. The header is prepended before data bytes. The header can contain information
           about the file.
        4. Send the file via websocket
        5. Update Redis
        """
        try:
            await asyncio.sleep(5)
            while True:
                msg = "Success"
                with await self.redis_pool as rdb:
                    task_json = (await rdb.blpop(self._rk("FILE", "FILES_SENDING_QUEUE")))[1]
                    task = json.loads(task_json)
                    file_path = task["FILE_PATH"]
                    box, box_ws = await self.pick_box(rdb, timeout=1)
                    if box_ws is None:
                        self.logger.warning("No available box to send file.")
                        continue
                try:
                    infile = open(file_path, "rb")
                    b_hdrs = wrapbh(task)
                    try:
                        await box_ws.send_bytes(b_hdrs + infile.read())
                    except TypeError:
                        self.logger.exception("Data is not bytes, bytearray or memoryview.")
                        msg = "Data is not bytes, bytearray or memoryview."
                    finally:
                        infile.close()
                    self.logger.debug("Send %s to %s" % (file_path, box))
                except IOError:
                    self.logger.exception("No such file %s" % file_path)
                    msg = "No such file."
                save_dict = {
                    "ID": box,
                    "MSG": msg,
                }
                save_dict.update(task)
                with await self.redis_pool as rdb:
                    self.logger.debug("Save SENT FILE %s" % (self._rk("FILE", "PROCESSED_FILES", file_path)))
                    await rdb.hmset_dict(self._rk("FILE", "PROCESSED_FILES", file_path), save_dict)
                    # prevent old information to interfere new information
                    await rdb.expire(self._rk("FILE", "PROCESSED_FILES", file_path), 30)
        except asyncio.CancelledError:
            return

    async def pick_box(self, rdb, timeout=1):
        """
        Pop boxes from the head of list and push them back to the tail
        :return box's id and box's web socket
        """
        random.seed(time.time())
        if not len(self._peers_ws):
            return (None, None)
        keys = [k for k, v in self._peers_ws.items()]
        box = None
        while len(keys):
            box = random.choice(keys)
            try:
                if self._peers_ws[box]['ws'] is not None:
                    return (box, self._peers_ws[box]['ws'])
            except:
                keys.remove(box)
        return (None, None)

    async def cleanup(self):
        """ Called when the loop stop """
        try:
            for box_id in list(self._peers_ws):
                if 'ws' in self._peers_ws[box_id].keys():
                    await self._peers_ws[box_id]['ws'].close()
            connect_box_tasks = list(self._connect_box_tasks)
            for b_id in connect_box_tasks:
                try:
                    self._connect_box_tasks[b_id].cancel()
                    await self._connect_box_tasks[b_id]
                except KeyError:
                    pass
            await super(PublisherAsyncClient, self).cleanup()
        except:
            pass


class FileManager:
    """
    This class is an api for other users to connect to Publisher. The basic usage for now is that
    users should push their file's name or directory, (assuming that user's process and Publisher
    are running  on the same machine, so that we could read the file locally by provided file's
    directory)to the queue, and then our zmq server would get the file name and assign a box to that
    file. Once the file is sent, users could check if the file is assigned to which box via this
    manager.
    Future development:
    - Users could send their files via network instead of local machine.
    """
    def __init__(self, id,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,):
        """
        :param id: publisher's id
        """
        self.id = id
        self._rk = RedisKeyWrapper(self.id)
        self.rdb = redis.StrictRedis(host=redis_address[0],
                                     port=redis_address[1],
                                     db=redis_db,
                                     decode_responses=True)

    def push(self, file_path, ttl=60, **kwargs):
        """
        :param ttl: if ttl is 0, then it will live forever in boxes, otherwise time unit is sec
        :param kwargs: other headers
        """
        assert(isinstance(file_path, str))
        d = {
            "FILE_PATH": file_path,
            "TTL": ttl,
        }
        d.update(kwargs)
        try:
            task = json.dumps(d)
            self.rdb.rpush(self._rk("FILE", "FILES_SENDING_QUEUE"), task)
        except TypeError:
            logging.exception("Item can't be serialized.")

    def ask(self, filename):
        """
        :param filename:  file's directory
        :return: dictionary of the filename in redis, if not exist then return empty dictionary
        """
        response = self.rdb.hgetall(self._rk("FILE", "PROCESSED_FILES", filename))
        if len(response):
            try:
                box_id = response["ID"]
                box_info = self.rdb.hgetall(self._rk("SEARCH", box_id))
                if not len(box_info):
                    logging.error("Can't find %s 's Info, return box's id only." % box_id)
                else:
                    response.update(box_info)
            except KeyError:
                logging.exception("Can't get Key ID")
        return response
