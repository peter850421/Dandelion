import sys
import asyncio
import aioredis
import logging
import redis
import os
import time
import uvloop
import re
from aiohttp import web
from .routes import setup_box_routes, setup_entrance_routes
from .utils import RedisKeyWrapper, create_id
from .logger import get_logger

if sys.version_info < (3, 5):
    raise Exception("must use python 3.5 or greater")

# Use uvloop as default
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class BaseAsyncServer(object):
    """
    - Base class for Asyncio Server

    - Extended from aiohttp, read Doc:
    http://aiohttp.readthedocs.io/en/stable/web_reference.html#aiohttp.web.Server

    - Box server and Service's (which distributes data among boxes) server should
    inherit this class and override methods for own purposes

    - Methods for the caller:
    - __init__(server_address, RequestHandlerClass)
    - serve_forever()

    - Methods that may be overridden:
    - initialize()
    - setup_routes()
    - setup_middlewares()
    - register_on_startup()
    - register_on_cleanup

    Parameters:
    :param id: An unique ID for this server
    :param ip: IP that server will listen to
    :param port: PORT on local machine that server binds to
    :param proxy_port: If nginx is used as a proxy server, then the proxy port is the port
                        that nginx listen to. It will proxy the coming request to param port.
                        This is recommended, because nginx can set up https.
    """

    def __init__(self, id,
                 ip,
                 port,
                 proxy_port=None,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=10,
                 redis_maxsize=20,
                 log_level=logging.DEBUG,
                 **kwargs):
        """Constructor.  May be extended, do not override."""
        self.id = id
        self.app = web.Application()
        self.ip = self.app["IP"] = ip
        self.port = self.app["PORT"] = port
        self.proxy_port = self.app["PROXY_PORT"] = proxy_port
        self._loop = loop if loop else asyncio.get_event_loop()
        asyncio.set_event_loop(self._loop)
        self._rk = RedisKeyWrapper(self.id)
        self.conf = {
            "redis_address": redis_address,
            "redis_db": redis_db,
            "redis_minsize": redis_minsize,
            "redis_maxsize": redis_maxsize,
        }
        self.app["conf"] = self.conf
        self.app['ID'] = self.id
        self.app["websockets"] = []
        self.setup_routes()
        self.setup_middlewares()
        self.app.on_startup.append(self.register_on_startup)
        self.app.on_cleanup.append(self.register_on_cleanup)
        self.rdp = None

    def __unicode__(self):
        return self.id

    def __del__(self):
        """ Called when instance is about to be destroyed. """
        pass

    def base_url(self, with_scheme=False):
        raise NotImplementedError

    def ws_url(self, with_scheme=False):
        return self.base_url(with_scheme=with_scheme) + 'ws/'

    @property
    def loop(self):
        return self._loop

    async def setup_aioredis(self):
        self.rdp = await aioredis.create_pool(self.conf["redis_address"],
                                              db=self.conf["redis_db"],
                                              minsize=self.conf["redis_minsize"],
                                              maxsize=self.conf["redis_minsize"],
                                              encoding="utf-8")
        self.app['redis_pool'] = self.rdp

    def setup_routes(self, **kwargs):
        """ Set up routes to handle requests from client"""
        pass

    def setup_middlewares(self, **kwargs):
        pass

    def serve_forever(self):
        """
        Start to run server

        - If other tasks would like to run along with server on the loop, you
          should ensure_future before calling serve_forever
        """
        web.run_app(self.app,
                    host="0.0.0.0",
                    port=self.port,
                    loop=self.loop
                    )

    async def register_on_startup(self, app):
        await self.setup_aioredis()

    async def register_on_cleanup(self, app):
        for ws in app['websockets']:
            await ws.close()
        self.rdp.close()
        await self.rdp.wait_closed()


class EntranceAsyncServer(BaseAsyncServer):
    def __init__(self, id,
                 ip,
                 port,
                 proxy_port=None,
                 loop=None,
                 redis_address=("127.0.0.1", 6379),
                 redis_db=0,
                 redis_minsize=10,
                 redis_maxsize=20,
                 expire_box_time=120,
                 amount_of_boxes_per_request=20,
                 background_task_freq=5,
                 log_level=logging.DEBUG,
                 other_entrances_urls=[],
                 mysql_host="0.0.0.0",
                 mysql_password='',
                 mysql_db='',
                 mysql_port=3306,
                 mysql_user='root',
                 **kwargs):
        self.logger = get_logger("Entrance", level=log_level)
        if "entrance-" not in id:
            self.logger.warning("ID does not contain entrance-")
            raise ValueError
        super().__init__(id,
                         ip=ip,
                         port=port,
                         proxy_port=proxy_port,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         **kwargs)
        self.app["logger"] = self.logger
        self.conf.update({
                "amount_of_boxes_per_request": amount_of_boxes_per_request,
                "expire_box_time": expire_box_time,
                "mysql_host": mysql_host,
                "mysql_password": mysql_password,
                "mysql_db": mysql_db,
                "mysql_user": mysql_user,
                "mysql_port": mysql_port,
        })
        # For websockets handlers get_own_info_dict
        self.app["ENTRANCE_URLS"] = self.ws_url(with_scheme=True)
        self.background_task_freq = background_task_freq
        self.store_other_entrances_urls(other_entrances_urls)

    def base_url(self, with_scheme=False):
        if with_scheme:
            # If proxy_port is not None, then assume that the proxy_port has opened up https
            if self.proxy_port:
                return 'https://{}:{}/dandelion/'.format(self.ip,
                                                         self.proxy_port)
            else:
                return 'http://{}:{}/dandelion/'.format(self.ip,
                                                        self.port)
        else:
            return '/dandelion/'

    def setup_routes(self):
        setup_entrance_routes(self.app)

    async def register_on_startup(self, app):
        await super(EntranceAsyncServer, self).register_on_startup(app)
        app["background_task"] = self.loop.create_task(self.background_task())

    async def register_on_cleanup(self, app):
        await super().register_on_cleanup(app=app)
        self.app["background_task"].cancel()
        await self.app["background_task"]

    def store_other_entrances_urls(self, other_entrance_urls):
        rdb = redis.StrictRedis(host=self.conf["redis_address"][0],
                                port=self.conf["redis_address"][1],
                                db=self.conf["redis_db"],
                                encoding="utf-8")
        rdb.sadd(self._rk("ENTRANCE_URLS"), *other_entrance_urls)

    async def background_task(self):
        """
        - Run in background, update entrance info and expire outdated boxes periodically
        """
        self.logger.info("Background task starts...")
        while True:
            try:
                with await self.rdp as rdb:
                    await self.update_entrance_info(rdb)
                    await self.expire_outdated_boxes(rdb)
                await asyncio.sleep(self.background_task_freq)
            except asyncio.CancelledError:
                break

    async def update_entrance_info(self, rdb):
        own_info = {"ID": self.id,
                    "TYPE": "ENTRANCE",
                    "IP": self.ip,
                    "PORT": self.port if not self.proxy_port else self.proxy_port}
        await rdb.hmset_dict(self._rk("OWN_INFO"), own_info)

    async def expire_outdated_boxes(self, rdb):
        outdated = await rdb.zrangebyscore(self._rk("BOX_SET"), min=0, max=int(time.time()))
        for box in outdated:
            await rdb.zrem(self._rk("BOX_SET"), box)
            await rdb.delete(self._rk("EXCHANGE", box))


class BoxAsyncServer(BaseAsyncServer):
    def __init__(self, id,
                 ip,
                 port,
                 proxy_port=None,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 redis_minsize=5,
                 redis_maxsize=10,
                 log_level=logging.DEBUG,
                 base_directory="/tmp",
                 expire_files_freq=10,
                 nginx_access_log='/var/log/nginx/nginx-access.log',
                 ping_entrance_freq=10,
                 **kwargs):
        self.logger = get_logger("Box-Server", level=log_level)
        if "box-" not in id:
            self.logger.warning("ID does not contain box-")
            raise ValueError
        super().__init__(id,
                         ip=ip,
                         port=port,
                         proxy_port=proxy_port,
                         loop=loop,
                         redis_address=redis_address,
                         redis_db=redis_db,
                         redis_minsize=redis_minsize,
                         redis_maxsize=redis_maxsize,
                         log_level=log_level,
                         **kwargs)
        self.app["logger"] = self.logger
        self.conf["base_directory"] = base_directory
        self.conf["nginx_access_log"] = nginx_access_log
        self.conf["ping_entrance_freq"] = ping_entrance_freq
        self.expire_files_freq = expire_files_freq

    def base_url(self, with_scheme=False):
        if with_scheme:
            # If proxy_port is not None, then assume that the proxy_port has opened up https
            if self.proxy_port:
                return 'https://{}:{}/dandelion/{}/'.format(self.ip,
                                                            self.proxy_port,
                                                            self.id)
            else:
                return 'http://{}:{}/dandelion/{}/'.format(self.ip,
                                                           self.port,
                                                           self.id)
        else:
            return '/dandelion/{}/'.format(self.id)

    def setup_routes(self):
        setup_box_routes(self.app)

    async def delete_expire_files(self):
        self.logger.info("---Start delete_expire_files task---")
        while True:
            try:
                with await self.rdp as rdb:
                    expire_files = await rdb.zrangebyscore(self._rk("EXPIRE_FILES"),
                                                           min=0,
                                                           max=int(time.time()))
                    if len(expire_files):
                        await rdb.zrem(self._rk("EXPIRE_FILES"), *expire_files)
                    else:
                        await asyncio.sleep(self.expire_files_freq)
                        continue
                for file in expire_files:
                    try:
                        os.remove(file)
                        self.logger.debug("Delete %s." % file)
                    except:
                        self.logger.exception("%s is not a file" % file)
                await asyncio.sleep(self.expire_files_freq)
            except asyncio.CancelledError:
                break

    async def update_nginx_log_file(self):
        """
        Read nginx-access.log file to calculate that how much flow does the box server helps
        publisher to distribute its files.
        """
        def extract_log_line(line):
            match = re.search(r'\[(?P<datetime>.+) \+0000\]-"[A-Z]{3,4} (?P<url>.+) HTTPS?/.+"-(?P<status>\d{3})-(?P<size>\d+)',
                          line)
            if match is None:
                return None
            else:
                return {
                    'datetime': match.group('datetime'),
                    'url': match.group('url'),
                    'status': int(match.group('status')),
                    'size': int(match.group('size'))
                }
        if self.proxy_port is None:
            return
        file_path = self.conf["nginx_access_log"]
        # wait for the first log create
        await asyncio.sleep(5)
        self.logger.info("-----Start reading %s from nginx" % file_path)
        infile = None
        try:
            while True:
                if not infile or infile.closed:
                    try:
                        infile = open(file_path)
                    except:
                        self.logger.exception("Can't open log file %s." % file_path)
                        await asyncio.sleep(5)
                        continue
                where = infile.tell()
                line = infile.readline()
                if line:
                    content = extract_log_line(line)
                    if content is None:
                        continue
                    with await self.rdp as rdb:
                        log_id = self._rk("TRAFFIC_FLOW", create_id("log"))
                        await rdb.hmset_dict(log_id, content)
                        await rdb.expire(log_id, self.conf["ping_entrance_freq"] * 2)
                else:
                    if where > 1024 * 1024:
                        infile.close()
                        os.remove(file_path)
                    else:
                        infile.seek(where)
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
                pass
        # Delete the log file,  so that it will not start from the old information at the next time
        try:
            if not infile and not infile.closed:
                infile.close()
            os.remove(file_path)
        except:
            pass

    async def register_on_startup(self, app):
        await super(BoxAsyncServer, self).register_on_startup(app)
        app["expire_files_task"] = asyncio.ensure_future(self.delete_expire_files())
        app["update_nginx_log_file_task"] = asyncio.ensure_future(self.update_nginx_log_file())

    async def register_on_cleanup(self, app):
        app["expire_files_task"].cancel()
        await app["expire_files_task"]
        app["update_nginx_log_file_task"].cancel()
        await app["update_nginx_log_file_task"]
        await super().register_on_cleanup(app=app)
