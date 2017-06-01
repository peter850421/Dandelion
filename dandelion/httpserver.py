import sys
import asyncio
import aioredis
import logging
import ssl
import os
import time
import uvloop
from aiohttp import web
from .routes import setup_box_routes, setup_entrance_routes
from .utils import RedisKeyWrapper
from .logger import get_logger

if sys.version_info < (3, 5):
    raise Exception("must use python 3.5 or greater")


class BaseAsyncServer(object):
    """
    - Base class for Asyncio Server

    - Extended from aiohttp, read Doc:
    http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Server

    - Box server and Service's (which distributes data among boxes) server should
    inherit this class and override methods for own process purposes

    - Methods for the caller:
    - __init__(server_address, RequestHandlerClass)
    - serve_forever()

    - Methods that may be overridden:
    - initialize()
    - setup_routes()
    - setup_middlewares()
    - register_on_startup()
    - register_on_cleanup
    """
    def __init__(self, id,
                 ip,
                 port,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=1,
                 redis_maxsize=5,
                 log_level=logging.DEBUG,
                 **kwargs):
        """Constructor.  May be extended, do not override."""
        self.id = id
        self.ip = ip
        self.port = port
        self._loop = loop if loop else uvloop.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._rk = RedisKeyWrapper(self.id)
        self.conf = {
            "redis_address":redis_address,
            "redis_db":redis_db,

        }
        self._loop.run_until_complete(asyncio.gather(self.initialize(redis_address=redis_address,
                                                                     redis_db=redis_db,
                                                                     redis_minsize=redis_minsize,
                                                                     redis_maxsize=redis_maxsize,
                                                                     **kwargs)))

    def __unicode__(self):
        return self.id

    def __del__(self):
        """ Called when instance is about to be destroyed. """
        pass

    async def initialize(self, **kw):
        """ Initialization, called in __init__ """
        self.app = web.Application(loop=self._loop)
        self.rdp = await aioredis.create_pool(kw["redis_address"],
                                              db=kw["redis_db"],
                                              minsize=kw["redis_minsize"],
                                              maxsize=kw["redis_minsize"],
                                              encoding="utf-8")
        self.app['redis_pool'] = self.rdp
        self.app["conf"] = self.conf
        self.app['ID'] = self.id
        self.app["websockets"] = []
        self.setup_routes()
        self.setup_middlewares()
        self.app.on_startup.append(self.register_on_startup)
        self.app.on_cleanup.append(self.register_on_cleanup)

    @property
    def loop(self):
        return self._loop

    def setup_routes(self, **kwargs):
        """ Set up routes to handle requests from client"""
        pass

    def setup_middlewares(self, **kwargs):
        pass

    def serve_forever(self, ssl_context=ssl.SSLContext(ssl.PROTOCOL_SSLv23)):
        """
        Start to run server

        - If other tasks would like to run along with server on the loop, you
          should ensure_future before calling serve_forever

        - if ssl_context is None, then http will be used instead of https
        """
        try:
            ROOT_DIR = os.environ["ROOT_DIR"]
        except KeyError:
            raise KeyError("ROOT_DIR is not defined.")
        CRT_PATH = os.path.join(ROOT_DIR, "server.crt")
        KEY_PATH = os.path.join(ROOT_DIR, "server.key")
        if not os.path.exists(CRT_PATH):
            raise FileNotFoundError("Can't find server.crt.")
        if not os.path.exists(KEY_PATH):
            raise FileNotFoundError("Can't find server.key.")
        if ssl:
            ssl_context.load_cert_chain(CRT_PATH, KEY_PATH)
        web.run_app(self.app,
                    host=self.ip,
                    port=self.port,
                    ssl_context=ssl_context)

    async def register_on_cleanup(self, app):
        self.rdp.close()
        await self.rdp.wait_closed()
        for ws in app['websockets']:
            await ws.close()

    async def register_on_startup(self, app):
        pass


class EntranceAsyncServer(BaseAsyncServer):
    def __init__(self, id,
                 ip=None,
                 port=None,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=1,
                 redis_maxsize=5,
                 expire_box_time=120,
                 amount_of_boxes_per_request=20,
                 log_level=logging.DEBUG,
                 **kwargs):
        if "entrance-" not in id:
            self.logger.warning("ID does not contain entrance-")
            raise ValueError
        super().__init__(id,
                         ip=ip,
                         port=port,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         **kwargs)
        self.logger = get_logger("Entrance", level=log_level)
        self.app["logger"] = self.logger
        self.conf["expire_box_time"] = expire_box_time
        self.conf["amount_of_boxes_per_request"] = amount_of_boxes_per_request

    def setup_routes(self):
        setup_entrance_routes(self.app)

    def register_on_startup(self, app):
        app["background_process"] = app.loop.create_task(self.background_process())

    async def register_on_cleanup(self, app):
        super().register_on_cleanup(app=app)
        self.app["background_process"].cancel()

    async def background_process(self):
        """
        - Run in background, update entrance info and expire outdated boxes periodically
        """
        self.logger.info("Background task starts...")
        while True:
            with await self.rdp as rdb:
                await self.update_entrance_info(rdb)
                await self.expire_outdated_boxes(rdb)
            await asyncio.sleep(5)

    async def update_entrance_info(self, rdb):
        own_info = {
            "ID": self.id,
            "TYPE": "EXTRANCE",
            "IP": self.ip,
            "PORT": self.port,
        }
        await rdb.hmset_dict(self._rk("OWN_INFO"), own_info)

    async def expire_outdated_boxes(self, rdb):
        outdated = await rdb.zrangebyscore(self._rk("BOX_SET"), min=0, max=int(time.time()))
        for i in outdated:
            await rdb.zrem(self._rk("BOX_SET"), i)
        for box in outdated:
            rdb.delete(self._rk("EXCHANGE", box))


class BoxAsyncServer(BaseAsyncServer):
    def __init__(self, id,
                 ip=None,
                 port=None,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=1,
                 redis_maxsize=5,
                 log_level=logging.DEBUG,
                 base_directory="/tmp",
                 **kwargs):
        if "box-" not in id:
            self.logger.warning("ID does not contain box-")
            raise ValueError

        super().__init__(id,
                         ip=ip,
                         port=port,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         log_level=log_level,
                         **kwargs)
        self.logger = get_logger("Box-Server", level=log_level)
        self.app["logger"] = self.logger
        self.conf["base_directory"] = base_directory

    def setup_routes(self):
        setup_box_routes(self.app)
