import asyncio
import logging
import random
import aioredis
import time
from aiohttp import ClientSession, WSMsgType, TCPConnector
import aiohttp
import uvloop
import ssl
import redis
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
                 redis_address=("localhost", 6379),
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

        asyncio.ensure_future(self.run())
        try:
            self.logger.info("{0} Async Client Loop Start...".format(self.id))
            self._loop.run_forever()
        except KeyboardInterrupt:
            self.logger.warning("KeyboardInterrupt.")
        self._loop.run_until_complete(asyncio.gather(self.cleanup()))
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
                self._entrance_ws[url] = ws
                await self.send_entrance(ws)
                async for msg in ws:
                    self.logger.debug(" RECEIVE MSG %s, FROM URL: %s" % (str(msg), url))
                    if msg.type == WSMsgType.TEXT:
                        await self._dispatch(msg, ws)
                        break
                    elif msg.type == WSMsgType.CLOSED:
                        break
                    elif msg.type == WSMsgType.ERROR:
                        break
        except (aiohttp.WSServerHandshakeError, aiohttp.errors.ClientOSError):
            self.logger.exception("Connection Failure to %s" % url, exc_info=False)
        except:
            self.logger.exception("Fail in connect_entrance")
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
        while True:
            await self.update_self_exchange()
            await asyncio.sleep(10)

    async def ping_entrances(self):
        while True:
            for url in self.entrance_urls:
                if url not in self._entrance_ws.keys():
                    asyncio.ensure_future(self.connect_entrance(url))
            await asyncio.sleep(self.conf["ping_entrance_freq"])

    async def on_EXCHANGE(self, msg, ws):
        try:
            id = msg["ID"]
            with await self.rdp as rdb:
                await rdb.hmset_dict(self._rk("EXCHANGE", id), msg)
        except KeyError:
            self.logger.exception("There's no key 'ID' in msg.")
        except:
            self.logger.exception("Fail while storing msg.")

    async def send_entrance(self, ws):
        with await self.rdp as rdb:
            self_exchange = await rdb.hgetall(self._rk("SELF_EXCHANGE"))
        self.ws_send(self_exchange, ws)

    async def update_self_exchange(self):
        """ Update Own Exchange Info """
        ip = self.ip
        if not ip:
            ip = await self._loop.run_in_executor(None, get_ip)
        connect_url = URLWrapper("http://"+ip+":"+self.conf["proxy_port"]+"/")("dandelion", self.id, "ws")
        ex_dict = {"ID": self.id,
                   "IP": ip,
                   "PORT": self.conf["proxy_port"],
                   "TYPE": "BOX",
                   "COMMAND": "EXCHANGE",
                   "CONNECT_WS": connect_url}
        with await self.rdp as rdb:
            await rdb.hmset_dict(self._rk("SELF_EXCHANGE"), ex_dict)

    async def peer_connect(self, url, type):
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
            await self.maintain_peers()
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
        await self._loop.run_in_executor(None, self.rank_boxes)
        with await self.rdp as rdb:
            box_list = await rdb.zrevrangebyscore(self._rk("BOX_RANKING"),
                                                  offset=0,
                                                  count=self.min_peers)
            for box in box_list:
                if box not in self._peers_ws.keys():
                    self._peers_ws[box] = None
                    asyncio.ensure_future(self.connect_box(box))

    def rank_boxes(self):
        """
        According to boxes info , rank boxes into a sorted set
        For now, just make every box with score 0
        """
        rdb = redis.StrictRedis(host=self.conf["redis_address"][0],
                                port=self.conf["redis_address"][1],
                                db=self.conf["redis_db"],
                                encoding="utf-8")
        boxes = rdb.keys(self._rk("SEARCH", "box*"))
        for box in boxes:
            box = gktail(box.decode())
            rdb.zadd(self._rk("BOX_RANKING"), 0, box)

    async def connect_box(self, box_id):
        with await self.rdp as rdb:
            url = (await rdb.hmget(self._rk("SEARCH", box_id), "CONNECT_WS"))[0]
        if url is None:
            return
        try:
            async with self.session.ws_connect(url) as ws:
                await self.send_box(ws)
                self._peers_ws[box_id] = ws
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
            self.logger.exception("Connection Failure to %s" % url, exc_info=False)
        except:
            self.logger.exception("Fail in connect_box %s" % box_id, exc_info=False)
        finally:
            self._peers_ws.pop(box_id, None)

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
                file_path = str((await rdb.blpop(self._rk("FILE", "FILES_SENDING_QUEUE")))[1])
                box, ws = await self.pick_box(rdb, timeout=1)
                if ws is None:
                    await rdb.lpush(self._rk("FILE", "FILES_SENDING_QUEUE"), file_path)
                    self.logger.warning("No available box to send file.")
                    await asyncio.sleep(3)
                    continue
            try:
                infile = open(file_path, "rb")
                headers = {
                    "FILE_PATH": file_path,
                }
                b_hdrs = wrapbh(headers)
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
            with await self.redis_pool as rdb:
                await rdb.hmset_dict(self._rk("FILE", "PROCESSED_FILES", file_path), save_dict)

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
        while True:
            box = random.choice(keys)
            if self._peers_ws[box] is not None:
                break
        return (box, self._peers_ws[box])

    async def cleanup(self):
        """ Called when the loop stop """
        await super().cleanup()
        for ws in self._peers_ws.keys():
            await self._peers_ws[ws].close()


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
                 redis_address=("localhost", 6379),
                 redis_db=0,):
        self.id = id
        self._rk = RedisKeyWrapper(self.id)
        self.rdb = redis.StrictRedis(host=redis_address[0],
                                     port=redis_address[1],
                                     db=redis_db)

    def push(self, filename):
        assert(isinstance(filename, str))
        self.rdb.rpush(self._rk("FILE", "FILES_SENDING_QUEUE"), filename)

    def ask(self, filename):
        """
        :param filename:  file's directory
        :return: dictionary of the filename in redis, if not exist then return none
        """
        response = self.rdb.hgetall(self._rk("FILE", "PROCESSED_FILES", filename))
        if response is not None:
            try:
                box_id = response["ID"]
                response.update(self.rdb.hgetall(self._rk("SEARCH", box_id)))
            except KeyError:
                logging.exception("Can't get Key ID")
        return response





# class PublisherZMQClient(PublisherAsyncClient):
#     async def run(self):
#         while True:
#             await self.ping_entrances()
#             await self.rank_boxes()
#             await self.maintain_peers()
#             await asyncio.sleep(self.config["PUBLISHER_RUN_UPDATE_FREQ"])
#
#     async def maintain_peers(self):
#         """
#         - Count currently connecting peers amount
#         - if the amount is under max_zmq_peers, then find peers from box ranking list
#         - Make the box subscribe
#         """
#         with await self.redis_pool as redis:
#             connecting_peers = await redis.zcount(self._rk("ZMQ", "EXPIRE_SET"))
#             offset = self.config["MAX_ZMQ_PEERS"] - connecting_peers
#             if offset <= 0: return
#             get_boxes = await redis.zrangebyscore(self._rk("BOX_RANKING"), min=0)
#             count = 0
#             for box in get_boxes:
#                 # If box is already in ZMQ EXPIRE_SET, it means that it already subscribes
#                 if not await redis.zrank(self._rk("ZMQ", "EXPIRE_SET"), box):
#                     asyncio.ensure_future(self.make_box_subscribe(box))
#                     count += 1
#                 if count == offset: return
#
#     async def make_box_subscribe(self, box_id):
#         with await self.redis_pool as redis:
#             box_data = await redis.hgetall(self._rk("SEARCH", box_id))
#         if not all(key in box_data for key in ["IP", "PORT"]):
#             self.logger.warning("No IP and PORT in %s data" % (box_id))
#             return
#         ip_url = "https://" + box_data["IP"] + ":" + box_data["PORT"]
#         wrap = URLWrapper(ip_url)
#         url = wrap(self.config["BASE_URL"], box_id, self.config["WEBSOCKET_URL"])
#         ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
#         conn = TCPConnector(ssl_context=ssl_context)
#         session = ClientSession(connector=conn)
#         try:
#             self.logger.debug("Trying to connect %s" % (url))
#             async with session.ws_connect(url) as ws:
#                 self._peers_ws[url] = ws
#                 await self.send_subscribe(ws)
#         except Exception as e:
#             """
#             This would be called anyway, remove the box from ranking and search.
#             We can get this box or other new boxes from pinging entrances, so no
#             need to save it inside out box
#             """
#             with await self.redis_pool as redis:
#                 # await redis.zrem(self._rk("BOX_RANKING"), box_id)
#                 await redis.expire(self._rk("SEARCH", box_id), 60)
#         finally:
#             await session.close()
#
#     async def send_subscribe(self, ws):
#         request = {
#             "ID": self.id,
#             "IP": self.ip,
#             "PORT": self.port,
#             "TYPE": "PUBLISHER",
#             "COMMAND": "SUBSCRIBE",
#             "ZMQ_PING_ADDRESS": self.config["ZMQ_PUBLISHER_COLLECTING_ADDRESS"],
#             "ZMQ_RECEIVE_ADDRESS": self.config["ZMQ_XPUB_ADDRESS"]
#         }
#         self.ws_send(request, ws)
