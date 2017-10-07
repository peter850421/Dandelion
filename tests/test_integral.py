import uvloop
import redis
import asyncio
import os
import logging
from aiohttp.test_utils import unittest_run_loop, teardown_test_loop
from dandelion.httpserver import BoxAsyncServer
from dandelion.httpclient import PublisherAsyncClient, BoxAsyncClient, FileManager
from dandelion.utils import create_id, ws_send_json, create_random_file_with_size, get_ip
from dandelion.utils import wrap_bytes_headers as wrapbh
# from dandelion.logger import get_logger
import unittest
import socket
import random
import time
import multiprocessing
import shutil

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging_level = logging.DEBUG

# Settings
total_test_rounds = 2
amount_of_sent_files_per_round = 5


class PublishingTestCase(object):
    def get_box_server(self):
        server_id = create_id("box")
        server = BoxAsyncServer(id=server_id,
                                ip='0.0.0.0',
                                port=7072,
                                log_level=logging_level,
                                redis_db=2,
                                base_directory="/tmp/{}".format(server_id))
        return server

    async def make_factory(self, app):
        await app.startup()
        return app.make_handler(loop=self.loop)

    def run_server(self):
        try:
            # Bind ip port
            server = self.box_server
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.bind((server.ip, server.port))
            loop.run_until_complete(server.app.startup())
            self.handler = loop.run_until_complete(self.make_factory(server.app))
            loop.run_until_complete(self.loop.create_server(self.handler,
                                                            sock=self._socket))
            loop.run_forever()
        finally:
            print("END")
            self._socket.close()

    def get_publisher(self):
        publisher = PublisherAsyncClient(id=create_id("publisher"),
                                         ip="0.0.0.0",
                                         loop=self.loop,
                                         redis_db=2,
                                         log_level=logging_level)
        self.loop.run_until_complete(publisher.setup_aioredis())
        return publisher

    async def prepare_settings(self):
        # prepare box id for publisher's rank_boxes() function
        data = {
            "ID": self.box_server.id,
            "IP": self.box_server.ip,
            "PORT": self.box_server.port,
            "TYPE": "BOX",
            "CONNECT_WS": self.box_server.ws_url(with_scheme=True)
        }
        print(self.box_server.base_url(with_scheme=True))
        self.redis.hmset(self.publisher._rk("SEARCH", self.box_server.id), data)
        # Create a dir for storing testing file
        self.test_dir = "/tmp/test"
        os.makedirs(self.test_dir, exist_ok=True)

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.logger = logging.getLogger('testing-process')
        self.publisher = self.get_publisher()
        self.box_server = self.get_box_server()
        self.redis = redis.StrictRedis(db=2, decode_responses=True)
        self.loop.run_until_complete(self.prepare_settings())
        self.publisher_running_task = asyncio.ensure_future(self.publisher.run())
        p = multiprocessing.Process(target=self.run_server)
        p.start()

    def tearDown(self):
        try:
            self.publisher_running_task.cancel()
            self.loop.run_until_complete(self.publisher_running_task)
            self.loop.run_until_complete(self.publisher.cleanup())
            # self.loop.run_until_complete(self.box_server.app.shutdown())
            # self.loop.run_until_complete(self.handler.shutdown())
            # self.loop.run_until_complete(self.box_server.app.cleanup())

        finally:
            self.redis.flushdb()
            # Clean up all the file
            shutil.rmtree(self.test_dir)
            shutil.rmtree(self.box_server.conf["base_directory"], ignore_errors=True)
            self.loop.close()

    def create_random_file(self):
        no = random.randint(1, 1000000)
        filename = os.path.join(self.test_dir, "file-{}.txt".format(no))
        create_random_file_with_size(filename, 5 * 1024 * 1024)
        return filename

    def get_ttl_for_file(self):
        return random.randint(5, 60)

    # @unittest_run_loop
    # async def test_sending_many_files_to_boxes_for_a_long_time(self):
    #     current_round = 1
    #     fm = FileManager(self.publisher.id, redis_db=2)
    #     errors = 0
    #     while True:
    #         if current_round > total_test_rounds:
    #             break
    #         self.logger.info("Round: {}/{}.".format(current_round, total_test_rounds))
    #         filename_with_time = dict()
    #         for i in range(amount_of_sent_files_per_round):
    #             file = await self.loop.run_in_executor(None, self.create_random_file)
    #             file_ttl = self.get_ttl_for_file()
    #             filename_with_time[file] = file_ttl + int(time.time())
    #             fm.push(file, file_ttl)
    #             self.logger.info("Create file {} with ttl {}.".format(file, file_ttl))
    #         await asyncio.sleep(20)
    #         break
        #     while len(filename_with_time):
        #         remove_item = []
        #         for f, t in filename_with_time.items():
        #             current_time = int(time.time())
        #             response = fm.ask(f)
        #             # Case 1: file hasn't been expired yet
        #             if t > current_time:
        #                 if response == {}:
        #                     self.logger.critical("File {} hasn't correctly been distributed.".format(f))
        #                     errors += 1
        #                     remove_item.append(f)
        #                 else:
        #                     box_id = response["ID"]
        #                     t = os.path.exists(os.path.join(self.box_server.conf["base_directory"],
        #                                                     self.publisher.id,
        #                                                     response["FILE_PATH"][1:]))
        #                     if not t:
        #                         self.logger.critical(
        #                             "File {} should be stored at {}.".format(f, box_id))
        #                         errors += 1
        #                         remove_item.append(f)
        #             # Case 2: file should be deleted
        #             elif t < current_time:
        #                 if response != {}:
        #                     box_id = response["ID"]
        #                     t = os.path.exists(os.path.join(self.box_server.conf["base_directory"],
        #                                                     self.publisher.id,
        #                                                     response["FILE_PATH"][1:]))
        #                     if t:
        #                         self.logger.critical(
        #                             "File {} should be deleted at {}".format(f, box_id))
        #                         errors += 1
        #                 remove_item.append(f)
        #         for f in remove_item:
        #             filename_with_time.pop(f)
        #         await asyncio.sleep(10)
        #     current_round = current_round + 1
        # self.logger.critical("TOTAL ERRORS: %d" % errors)
