import asyncio
import logging
from multiprocessing import Process
from .httpclient import BoxAsyncClient, PublisherAsyncClient
from .httpserver import BoxAsyncServer, EntranceAsyncServer
import uvloop


class Box:
    def __init__(self, id, ip, port,
                 entrance_urls,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 server_redis_minsize=1,
                 server_redis_maxsize=5,
                 client_redis_minsize=1,
                 client_redis_maxsize=3,
                 ping_entrance_freq=10,
                 log_level=logging.DEBUG,
                 base_directory="/tmp",
                 **kwargs):
        self.conf = {
            "id": id,
            "ip": ip,
            "port": port,
            "entrance_urls": entrance_urls,
            "redis_address": redis_address,
            "redis_db": redis_db,
            "server_redis_minsize": server_redis_minsize,
            "server_redis_maxsize": server_redis_maxsize,
            "client_redis_minsize": server_redis_minsize,
            "client_redis_maxsize": server_redis_maxsize,
            "ping_entrance_freq": ping_entrance_freq,
            "log_level": log_level,
            "base_directory": base_directory,
        }
        self.server = BoxAsyncServer(id=self.conf["id"],
                                     ip=self.conf["ip"],
                                     port=self.conf["port"],
                                     redis_address=self.conf["redis_address"],
                                     redis_db=self.conf["redis_db"],
                                     redis_minsize=self.conf["server_redis_minsize"],
                                     redis_maxsize=self.conf["server_redis_maxsize"],
                                     base_directory=self.conf["base_directory"],
                                     log_level=self.conf["log_level"],
                                     )
        self.client_process = Process(target=self._start_client)

    def _start_client(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = BoxAsyncClient(id=self.conf["id"],
                                ip=self.conf["ip"],
                                port=self.conf["port"],
                                loop=loop,
                                entrance_urls=self.conf["entrance_urls"],
                                redis_address=self.conf["redis_address"],
                                redis_db=self.conf["redis_db"],
                                redis_minsize=self.conf["client_redis_minsize"],
                                redis_maxsize=self.conf["client_redis_maxsize"],
                                ping_entrance_freq=self.conf["ping_entrance_freq"],
                                log_level=self.conf["log_level"],
                                )
        client.start()

    def start(self):
        self.client_process.start()
        self.server.serve_forever()


class Publisher(PublisherAsyncClient):
    pass


class Entrance(EntranceAsyncServer):
    pass
