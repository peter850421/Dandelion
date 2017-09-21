import uvloop
import redis
import asyncio
import os
import shutil
import logging
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import WSMsgType
from aiohttp import web
from dandelion.httpserver import BoxAsyncServer
from dandelion.httpclient import PublisherAsyncClient, BoxAsyncClient
from dandelion.utils import create_id, ws_send_json, create_random_file_with_size, get_ip
from dandelion.utils import wrap_bytes_headers as wrapbh

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging_level = logging.CRITICAL


class BaseBoxTestCase(AioHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        cls.id = create_id("box")
        # Make sure that redis can be connected.
        # Use db=2 as testing database
        # decode_response must open, otherwise data received from redis will be bytes
        cls.redis_test = redis.StrictRedis(db=2, decode_responses=True)

    def tearDown(self):
        self.redis_test.flushdb()
        super().tearDown()


class BoxServerTestCase(BaseBoxTestCase):
    async def get_application(self):
        self.box_server = BoxAsyncServer(id=self.id,
                                         ip="127.0.0.1",
                                         redis_db=2,
                                         port=8080,
                                         loop=self.loop,
                                         log_level=logging_level,
                                         expire_files_freq=0.5)
        return self.box_server.app

    def get_publisher(self):
        return PublisherAsyncClient(id=create_id('publisher'),
                                    ip="127.0.0.1",
                                    loop=self.loop)

    @unittest_run_loop
    async def test_no_id_in__init__(self):
        with self.assertRaises(ValueError):
            box = BoxAsyncServer(id="123456", ip="127.0.0.1", port=8080, log_level=logging_level)

    @unittest_run_loop
    async def test_can_view_index(self):
        request = await self.client.get("/dandelion/" + self.id + "/")
        assert request.status == 200
        text = await request.text()
        self.assertEqual(text, "HI {0}".format(self.id))

    @unittest_run_loop
    async def test_ws_handler_on_PUBLISH(self):
        publisher = self.get_publisher()
        ws = await self.client.ws_connect(self.box_server.ws_url())
        sent_data = {
            "ID": publisher.id,
            "IP": publisher.ip,
            "TYPE": "PUBLISHER",
            "COMMAND": "PUBLISH"
        }
        await ws_send_json(sent_data, ws)
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                msg = msg.json()
                self.assertEqual(msg["MESSAGE"], "ACCEPTED")
                self.assertEqual(msg["COMMAND"], "PUBLISH")
                await ws.close()
                break
            elif msg.type == WSMsgType.CLOSED:
                break
            elif msg.type == WSMsgType.ERROR:
                break
        publisher_folder = os.path.join(self.box_server.conf["base_directory"], publisher.id)
        self.assertTrue(os.path.exists(publisher_folder))
        # clear folder
        shutil.rmtree(publisher_folder)
        with await self.box_server.rdp as rdb:
            redis_data = await rdb.hgetall(self.box_server._rk("EXCHANGE", publisher.id))
        for k, v in sent_data.items():
            # Redis will change int to str
            self.assertEqual(redis_data[k], str(v))

    @unittest_run_loop
    async def test_ws_handler_on_PUBLISH_with_None_value(self):
        publisher = self.get_publisher()
        ws = await self.client.ws_connect(self.box_server.ws_url())
        sent_data = {
            "ID": publisher.id,
            "IP": None,
            "TYPE": "PUBLISHER",
            "COMMAND": "PUBLISH"
        }
        await ws_send_json(sent_data, ws)
        # ERROR should be exists in the received msg
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                msg = msg.json()
                self.assertIn("ERROR", msg)
                self.assertIn("Wrong format in your message", msg["ERROR"])
            elif msg.type == WSMsgType.CLOSED:
                break
            elif msg.type == WSMsgType.ERROR:
                break

    @unittest_run_loop
    async def test_ws_handler_on_PUBLISH_without_key_TYPE(self):
        publisher = self.get_publisher()
        ws = await self.client.ws_connect(self.box_server.ws_url())
        sent_data = {
            "ID": publisher.id,
            "IP": '127.0.0.1',
            "COMMAND": "PUBLISH"
        }
        await ws_send_json(sent_data, ws)
        # ERROR should be exists in the received msg
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                msg = msg.json()
                self.assertIn("ERROR", msg)
                self.assertIn("Wrong format in your message", msg["ERROR"])
            elif msg.type == WSMsgType.CLOSED:
                break
            elif msg.type == WSMsgType.ERROR:
                break

    @unittest_run_loop
    async def test_ws_handler_on_BINARY(self):
        async def send_file(path, headers, ws):
            hdr = wrapbh(headers)
            infile = open(path, "rb")
            await ws.send_bytes(hdr + infile.read())
            infile.close()

        publisher = self.get_publisher()
        sent_data = {
            "ID": publisher.id,
            "IP": '127.0.0.1',
            "TYPE": "PUBLISHER",
            "COMMAND": "PUBLISH"
        }
        ws = await self.client.ws_connect(self.box_server.ws_url())
        await ws_send_json(sent_data, ws)
        file_path = "/tmp/test.txt"
        create_random_file_with_size(file_path, 1024 * 1024)
        headers = {
            "FILE_PATH": file_path,
            "TTL": "0"
        }
        await send_file(file_path, headers, ws)
        store_path = os.path.join(self.box_server.conf["base_directory"],
                                  publisher.id,
                                  file_path[1:])
        # Box server needs time to write file
        await asyncio.sleep(1)
        self.assertTrue(os.path.exists(store_path))
        os.remove(store_path)
        # Case 2: Make sure that delete_files_process is working, set ttl=1
        headers = {
            "FILE_PATH": file_path,
            "TTL": "1"
        }
        await send_file(file_path, headers, ws)
        await asyncio.sleep(1.5)
        self.assertFalse(os.path.exists(store_path))
        shutil.rmtree(os.path.join(self.box_server.conf["base_directory"],
                                   publisher.id))
        os.remove(file_path)
        await ws.close()


class BoxClientTestCase(BaseBoxTestCase):
    def tearDown(self):
        self.loop.run_until_complete(self.box_client.cleanup())
        super().tearDown()

    async def get_box_client(self):
        self.box_client = BoxAsyncClient(id=self.id,
                                         redis_db=2,
                                         port=8000,
                                         loop=self.loop,
                                         log_level=logging_level)
        await self.box_client.setup_aioredis()

    async def get_application(self):
        app = web.Application()
        await self.get_box_client()
        return app

    @unittest_run_loop
    async def test_update_self_exchange(self):
        await self.box_client.update_self_exchange()
        ex = self.redis_test.hgetall(self.box_client._rk("SELF_EXCHANGE"))
        ip = await get_ip()
        port = self.box_client.conf["proxy_port"]
        data = {"ID": self.id,
                "IP": ip,
                "PORT": port,
                "TYPE": "BOX",
                "COMMAND": "EXCHANGE",
                "CONNECT_WS": "https://{}:{}/dandelion/{}/ws/".format(ip, port, self.id)}
        for k, v in data.items():
            self.assertEqual(v, data[k])
