import asyncio
import json
import logging
import os
import random
import aioredis
import time
from aiohttp import ClientSession, WSMsgType, TCPConnector
import aiohttp
import uvloop
import ssl
import redis
from .systeminfo import CPU_loading_info, Memory_info, Loadaverage_info, Disk_info, CPU_number,CPU_Hz
from .utils import RedisKeyWrapper, URLWrapper
from .utils import get_key_tail as gktail
from .utils import wrap_bytes_headers as wrapbh
from .utils import get_ip
from .logger import get_logger


class BaseAsyncClient(object):
    def __init__(self, id, port,
                 entrance_urls,
                 ip=None,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=1,
                 redis_maxsize=5,
                 ping_entrance_freq=5,
                 log_level=logging.DEBUG, **kwargs):
        self.id = id
        self.ip = ip
        self.port = port
        self._loop = loop if loop else uvloop.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._queue_set = {}
        self.entrance_urls = set(entrance_urls)
        self._entrance_ws = dict()
        self._peers_ws = dict()
        self._rk = RedisKeyWrapper(self.id)
        self.conf = {
            "ping_entrance_freq": ping_entrance_freq,
            "redis_address": redis_address,
            "redis_db": redis_db,
        }
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        conn = TCPConnector(ssl_context=ssl_context)
        self.session = ClientSession(connector=conn)
        self.logger = get_logger("AsyncClient", level=log_level)
        self._loop.run_until_complete(asyncio.gather(self.initialize(redis_address=redis_address,
                                                                     redis_db=redis_db,
                                                                     redis_minsize=redis_minsize,
                                                                     redis_maxsize=redis_maxsize,
                                                                     )))


    @property
    def redis_pool(self):
        return self.rdp

    async def initialize(self, **kw):
        """Place required functions here before run() loop starts"""
        self.rdp = await aioredis.create_pool(kw["redis_address"],
                                              db=kw["redis_db"],
                                              minsize=kw["redis_minsize"],
                                              maxsize=kw["redis_minsize"],
                                              encoding="utf-8")

    def start(self):
        """Start process individually, otherwise register on server process"""

        run_task = asyncio.ensure_future(self.run())
        try:
            self.logger.info("{0} Async Client Loop Start...".format(self.id))
            self._loop.run_forever()
        except KeyboardInterrupt:
            self.logger.warning("KeyboardInterrupt.")
        self._loop.run_until_complete(asyncio.gather(self.cleanup()))
        run_task.cancel()
        self._loop.close()
        self.logger.info("{0} Async Client Loop Stop!".format(self.id))

    async def run(self):
        """Override this method"""
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
                async for msg in ws:
                    self.logger.debug(" RECEIVE MSG %s, FROM URL: %s." % (str(msg), url))
                    if msg.type == WSMsgType.TEXT:
                        await self._dispatch(msg, ws)
                        break
                    elif msg.type == WSMsgType.CLOSED:
                        break
                    elif msg.type == WSMsgType.ERROR:
                        break
        except (aiohttp.WSServerHandshakeError, aiohttp.errors.ClientOSError):
            self.logger.exception("Unable to connect to %s." % url, exc_info=False)
        except:
            self.logger.exception("Fail in connect_entrance.")
        finally:
            self._entrance_ws.pop(url, None)

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

    async def on_DEFAULT(self, msg, ws):
        pass

    def ws_send(self, request, ws):
        """
        :param request: dict
        """
        try:
            ws.send_json(request)
        except ValueError:
            self.logger.exception("Could not serialize self_exchange.")
        except (RuntimeError, TypeError):
            self.logger.exception("Could not send_json().")

    async def cleanup(self):
        """ Called when the loop stop """
        self.logger.info("Cleaning up entrance websockets...")
        self.rdp.close()
        await self.rdp.wait_closed()
        await self.session.close()
        for ws in self._entrance_ws.keys():
            await self._entrance_ws[ws].close()

    async def register_on_startup(self, app):
        app["client_process"] = app.loop.create_task(self.run())

    async def register_on_cleanup(self, app):
        await self.cleanup()
        app["client_process"].cancel()
        await app["client_process"]


class BoxAsyncClient(BaseAsyncClient):

    def __init__(self, id, port,
                 entrance_urls=None,
                 ip=None,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=1,
                 redis_maxsize=5,
                 ping_entrance_freq=10,
                 proxy_port=8000,
                 log_level=logging.DEBUG, **kwargs):
        """
        :param port: where server is listening to
        :param ip: set ip to None if it is not static
        :param proxy_port: we assume that proxy server is used
        """
        if "box-" not in id:
            self.logger.warning("ID does not contain box-")
            raise ValueError
        super().__init__(id, port, entrance_urls,
                         ip=ip,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         ping_entrance_freq=ping_entrance_freq)
        self.logger = get_logger("Box-Client", level=log_level)
        self.conf.update({
            "proxy_port": proxy_port
        })

    async def run(self):
        await self.update_self_exchange()
        asyncio.ensure_future(self.ping_entrances())
        asyncio.ensure_future(self.delete_expire_files())
        while True:
            await(self.update_self_exchange())
            await asyncio.sleep(10)

    async def ping_entrances(self):
        while True:
            for url in self.entrance_urls:
                if url not in self._entrance_ws.keys():
                    asyncio.ensure_future(self.connect_entrance(url))
            await asyncio.sleep(self.conf["ping_entrance_freq"])

    async def on_EXCHANGE(self, msg, ws):
        try:
            box_id = msg["ID"]
            with await self.rdp as rdb:
                await rdb.hmset_dict(self._rk("EXCHANGE", box_id), msg)
        except KeyError:
            self.logger.exception("There's no key 'ID' in msg.")
        except:
            self.logger.exception("Fail while storing msg.")

    async def send_entrance(self, ws):
        with await self.rdp as rdb:
            self_exchange = await rdb.hgetall(self._rk("SELF_EXCHANGE"))
        self.ws_send(self_exchange, ws)
        self.logger.info("SEND Msg to ENTRANCE : %s" % str(self_exchange))

    async def update_self_exchange(self):
        """ Update Own Exchange Info """
        ip = get_ip()
        connect_url = URLWrapper("http://"+ip+":"+str(self.conf["proxy_port"])+"/")("dandelion", self.id, "ws")
        CPU = CPU_loading_info()
        Load = Loadaverage_info()
        Memory = Memory_info()
        Disk = Disk_info()
        ex_dict = {"ID"            : self.id,
                   "IP"            : ip,
                   "PORT"          : self.conf["proxy_port"],
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
                   "DISK-AVAIL"    : Disk[1]}

        with await self.rdp as rdb:
            await rdb.hmset_dict(self._rk("SELF_EXCHANGE"), ex_dict)
        self.logger.debug("UPDATE SELF EXCHANGE %s" % str(ex_dict))

     async def delete_expire_files(self):
        while True:
            self.logger.debug("---Delete_expire_fires---")
            with await self.rdp as rdb:
                expire_files = await rdb.zrangebyscore(self._rk("EXPIRE_FILES"),
                                                   min=0,
                                                   max=int(time.time()))
                if len(expire_files):
                    await rdb.zrem(self._rk("EXPIRE_FILES"), *expire_files)
                else:
                    await asyncio.sleep(10)
                    continue
            for file in expire_files:
                try:
                   os.remove(file)
                except :
                   self.logger.warning("file %s is not a file or dir." %file )
                else:
                   self.logger.debug("Delete %s." % file)
            await asyncio.sleep(10)

    async def peer_connect(self, url, type):
        """ This method is designed to connect box and box so that boxes can communicate
            even if entrance server is down
        """
        pass


class PublisherAsyncClient(BaseAsyncClient):
    def __init__(self, id, port,
                 entrance_urls,
                 ip=None,
                 min_http_peers=10,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=5,
                 redis_maxsize=10,
                 ping_entrance_freq=3,
                 log_level=logging.DEBUG, **kwargs):

        if ip is None:
            ip = get_ip()
        if "publisher-" not in id:
            self.logger.warning("ID does not contain publisher-")
            raise ValueError
        super().__init__(id, port,
                         entrance_urls,
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
        self._peers_ws = dict()

    async def run(self):
        asyncio.ensure_future(self.collecting())
        asyncio.ensure_future(self.publish())
        while True:
            asyncio.ensure_future(self.maintain_peers())
            await asyncio.sleep(3)

    async def collecting(self):
        while True:
            for url in self.entrance_urls:
                if url not in self._entrance_ws.keys():
                    # Create key first, in case that duplicate socket has created
                    self._entrance_ws[url] = None
                    asyncio.ensure_future(self.connect_entrance(url))
            await asyncio.sleep(self.conf["ping_entrance_freq"])

    async def send_entrance(self, ws):
        """
        COMMAND: SEARCH
        """
        request = {
            "ID": self.id,
            "IP": self.ip,
            "PORT": self.port,
            "TYPE": "PUBLISHER",
            "COMMAND": "SEARCH",
        }
        self.ws_send(request, ws)

    async def on_SEARCH(self, msg, ws):
        with await self.rdp as rdb:
            if len(msg["BOX_SET"]):
                try:
                    for box_id in msg["BOX_SET"].keys():
                        await rdb.hmset_dict(self._rk("SEARCH", box_id),
                                             msg["BOX_SET"][box_id])
                except KeyError:
                    self.logger.exception("Key failure.")

    async def maintain_peers(self):
        """
        - First rank all known boxes in redis, the algorithm is implemented at rank_boxes
        - According to the ranking, pick boxes with higher scores and then make connection
        - Record it to the database
        """
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
                    asyncio.ensure_future(self.connect_box(box_id))

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
            self.logger.info("BOX_RANKING BOX-%s"%(box) )
            rdb.zadd(self._rk("BOX_RANKING"), 0, box)

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
                async for msg in ws:
                    self.logger.debug("RECEIVE MSG %s, FROM URL: %s" % (str(msg), url))
                    if msg.type == WSMsgType.TEXT:
                        await self._dispatch(msg, ws)
                    elif msg.type == WSMsgType.CLOSED:
                        break
                    elif msg.type == WSMsgType.ERROR:
                        break
        except (aiohttp.WSServerHandshakeError, aiohttp.errors.ClientOSError):
            self.logger.exception("Unable to connect to %s." % url, exc_info=False)
        except:
            self.logger.exception("Fail in connect_box %s" % box_id, exc_info=False)
        finally:
            self._peers_ws.pop(box_id, None)
            with await self.rdp as rdb:
                await rdb.zrem(self._rk("BOX_RANKING"), box_id)

    async def send_box(self, ws):
        message = {
            "ID": self.id,
            "IP": self.ip,
            "PORT": self.port,
            "TYPE": "PUBLISHER",
            "COMMAND": "PUBLISH"
        }
        self.ws_send(message, ws)

    async def publish(self):
        while True:
            msg = "Success"
            with await self.redis_pool as rdb:
                task_json = (await rdb.blpop(self._rk("FILE", "FILES_SENDING_QUEUE")))[1]
                task = json.loads(task_json)
                file_path = task["FILE_PATH"]
                box, ws = await self.pick_box(rdb, timeout=1)
                if ws is None:
                    await rdb.lpush(self._rk("FILE", "FILES_SENDING_QUEUE"), task_json)
                    self.logger.warning("No available box to send file.")
                    await asyncio.sleep(3)
                    continue
            try:
                infile = open(file_path, "rb")
                b_hdrs = wrapbh(task)
                try:
                    ws.send_bytes(b_hdrs + infile.read())
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
                #prevent old information to interferrence new informaion
                await rdb.expire(self._rk("FILE", "PROCESSED_FILES", file_path),30)

    async def pick_box(self, rdb, timeout=1):
        """
        Pop boxes from the head of list and push them back to the tail
        :return box's id and box's web socket
        """
        # box = await rdb.blpop(self._rk("FILE", "BOX_LIST"),
        #                       timeout=timeout)
        # if box is None:
        #     return None
        # await rdb.rpush(self._rk("FILE", "BOX_LIST"), box)
        # try:
        #     ws = self._peers_ws[box]
        # except KeyError:
        #     self.logger.warning("Box is in FILE:BOX_LIST, but can't find corresponding websocket.")
        #     return None
        # return (box, ws)
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
        await super().cleanup()
        for box_id in self._peers_ws.keys():
            await self._peers_ws[box_id]['ws'].close()


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
        :return: dictionary of the filename in redis, if not exist then return none
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
