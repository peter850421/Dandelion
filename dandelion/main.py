import asyncio
import uvloop
import logging
import multiprocessing
from .httpclient import BoxAsyncClient, PublisherAsyncClient
from .httpserver import BoxAsyncServer, EntranceAsyncServer

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Box:
    def __init__(self, id, server_ip, port,
                 entrance_urls,
                 client_ip=None,
                 loop=None,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 server_redis_minsize=1,
                 server_redis_maxsize=5,
                 client_redis_minsize=1,
                 client_redis_maxsize=3,
                 ping_entrance_freq=10,
                 proxy_port=None,
                 log_level=logging.DEBUG,
                 base_directory="/tmp",
                 **kwargs):
        self.conf = {
            "id": id,
            "server_ip": server_ip,
            "client_ip": client_ip,
            "port": port,
            "entrance_urls": entrance_urls,
            "redis_address": redis_address,
            "redis_db": redis_db,
            "server_redis_minsize": server_redis_minsize,
            "server_redis_maxsize": server_redis_maxsize,
            "client_redis_minsize": client_redis_minsize,
            "client_redis_maxsize": client_redis_maxsize,
            "ping_entrance_freq": ping_entrance_freq,
            "proxy_port": proxy_port,
            "log_level": log_level,
            "base_directory": base_directory,
        }

    def _start_client(self):
        client = BoxAsyncClient(id=self.conf["id"],
                                port=self.conf["port"],
                                entrance_urls=self.conf["entrance_urls"],
                                ip=self.conf["client_ip"],
                                redis_address=self.conf["redis_address"],
                                redis_db=self.conf["redis_db"],
                                redis_minsize=self.conf["client_redis_minsize"],
                                redis_maxsize=self.conf["client_redis_maxsize"],
                                ping_entrance_freq=self.conf["ping_entrance_freq"],
                                proxy_port=self.conf["proxy_port"],
                                log_level=self.conf["log_level"],
                                )
        client.start()

    def _start_server(self):
        self.server = BoxAsyncServer(id=self.conf["id"],
                                     ip=self.conf["server_ip"],
                                     port=self.conf["port"],
                                     proxy_port=self.conf["proxy_port"],
                                     redis_address=self.conf["redis_address"],
                                     redis_db=self.conf["redis_db"],
                                     redis_minsize=self.conf["server_redis_minsize"],
                                     redis_maxsize=self.conf["server_redis_maxsize"],
                                     base_directory=self.conf["base_directory"],
                                     ping_entrance_freq=self.conf["ping_entrance_freq"],
                                     log_level=self.conf["log_level"],
                                     )
        self.server.serve_forever()

    def start(self):
        client_process = multiprocessing.Process(target=self._start_client)
        try:
            client_process.start()
            self._start_server()
        finally:
            client_process.terminate()
            client_process.join()


class Publisher(PublisherAsyncClient):
    pass


class Entrance(EntranceAsyncServer):
    pass

__all__ = ("Box", "Publisher", "Entrance")
