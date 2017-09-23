from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from dandelion.utils import create_id, RedisKeyWrapper
from dandelion.httpserver import EntranceAsyncServer
from dandelion.httpclient import PublisherAsyncClient, BoxAsyncClient
import redis
import asyncio
import uvloop
import logging
import time
import random

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
logging_level = logging.CRITICAL


class BaseEntranceClientTestCase(AioHTTPTestCase):
    @classmethod
    def setUpClass(cls):
        cls.id = create_id("entrance")
        # Make sure that redis server can be connected.
        # Use db=2 as testing database
        # decode_response must open, otherwise data received from redis will be bytes
        cls.redis = redis.StrictRedis(db=2, decode_responses=True)

    def tearDown(self):
        self.redis.flushdb()


class EntranceServerTestCase(BaseEntranceClientTestCase):
    async def get_application(self):
        self.other_entrance_urls_example = [
           'http://127.0.0.1:8083/dandelion/entrance-123/ws/',
           'http://192.168.1.1:8000/dandelion/entrance-888/ws/',
           'http://192.168.1.5:8000/dandelion/entrance-100022/ws/'
        ]
        self.entrance = EntranceAsyncServer(id=self.id,
                                            ip="127.0.0.1",
                                            redis_db=2,
                                            port=7070,
                                            loop=self.loop,
                                            log_level=logging_level,
                                            amount_of_boxes_per_request=20,
                                            background_task_freq=1,
                                            other_entrances_urls=self.other_entrance_urls_example)
        return self.entrance.app

    async def get_publisher(self):
        self.publisher = PublisherAsyncClient(id=create_id("publisher"),
                                              ip="127.0.0.1",
                                              loop=self.loop,
                                              redis_db=2,
                                              log_level=logging_level)
        await self.publisher.setup_aioredis()

    async def get_box_client(self):
        self.box_client = BoxAsyncClient(id=create_id("box"),
                                         ip='127.0.0.1',
                                         port=7071,
                                         loop=self.loop,
                                         redis_db=2,
                                         proxy_port=8000,
                                         log_level=logging_level)
        await self.box_client.setup_aioredis()
        pass

    def tearDown(self):
        if hasattr(self, "publisher"):
            self.loop.run_until_complete(self.publisher.cleanup())
        if hasattr(self, "box_client"):
            self.loop.run_until_complete(self.box_client.cleanup())
        super(EntranceServerTestCase, self).tearDown()

    @unittest_run_loop
    async def test_store_other_entrances_urls(self):
        urls = self.redis.smembers(self.entrance._rk("ENTRANCE_URLS"))
        for item in self.other_entrance_urls_example:
            self.assertIn(item, urls)
        self.assertEqual(len(urls), len(self.other_entrance_urls_example))

    @unittest_run_loop
    async def test_send_SEARCH_to_entrance_from_publisher(self):
        await self.get_publisher()
        box_list = list()
        _rk = RedisKeyWrapper(self.entrance.id)
        for i in range(0, 30):
            data = {
                "ID": "box-{}".format(str(i)),
                "IP": "127.0.0.1",
                "PORT": 8080,
                "TYPE": "BOX"
            }
            box_list.append(int(time.time()) + random.randint(0, 100))
            box_list.append(data["ID"])
            self.redis.hmset(_rk("EXCHANGE", data["ID"]), data)

        self.redis.zadd(_rk("BOX_SET"), *box_list)
        # Connect to entrance
        ws = await self.client.ws_connect(self.entrance.ws_url())
        # Send Search to entrance
        await self.publisher.send_entrance(ws)
        # Wait for entrance to response
        response = await ws.receive()
        # Dump the message
        response = response.json()
        # Make sure that entrance returns 20 boxes
        self.assertEqual(len(response["BOX_SET"]), 20)
        # Throw the received message to on_SEARCH
        await self.publisher.on_SEARCH(response, ws)
        for box_id in response["BOX_SET"].keys():
            self.assertIn("box-", response["BOX_SET"][box_id]["ID"])
            # Comfirm that on_SEARCH has stored the BOX_SET into redis correctly
            self.assertTrue(self.redis.exists(self.publisher._rk("SEARCH", box_id)))

    @unittest_run_loop
    async def test_send_EXCHANGE_to_entrance_from_box(self):
        # Get box client instance
        await self.get_box_client()
        # Prepare correct exchange dictionary
        ex_dict = {"ID": self.box_client.id,
                   "IP": self.box_client.ip,
                   "PORT": self.box_client.port if not self.box_client.conf["proxy_port"] \
                       else self.box_client.conf["proxy_port"],
                   "TYPE": "BOX",
                   "COMMAND": "EXCHANGE"
                   }
        self.redis.hmset(self.box_client._rk("SELF_EXCHANGE"), ex_dict)
        # Connect to box
        ws = await self.client.ws_connect(self.entrance.ws_url())
        # Send EXCHANGE to entrance
        await self.box_client.send_entrance(ws)
        # Get response from entrance server
        response = (await ws.receive()).json()
        # Assert entrance has accepted
        self.assertIn("MESSAGE", response)
        self.assertIn("ACCEPTED", response["MESSAGE"])
        # Assert that entrance_urls are right
        self.assertIn("ENTRANCE_URLS",response)
        for url in self.other_entrance_urls_example:
            self.assertIn(url, response["ENTRANCE_URLS"])
        # Should also include the entrance server's ws url
        self.assertIn(self.entrance.ws_url(with_scheme=True), response["ENTRANCE_URLS"])
        # Assert that entrance server has stored the box into its redis correctly
        self.assertTrue(self.redis.exists(self.entrance._rk("EXCHANGE", self.box_client.id)))
        stored_ex = self.redis.hgetall(self.entrance._rk("EXCHANGE", self.box_client.id))
        for key, val in ex_dict.items():
            self.assertIn(key, stored_ex)
            self.assertEqual(str(val), stored_ex[key])

    @unittest_run_loop
    async def test_expire_outdated_boxes(self):
        # Setup test cases
        for i in range(1, 4):
            box_id = "box-{}".format(str(i))
            # I set up three boxes which have three different time.
            # Function expire_outdated_boxes should remove the box that is smaller than
            # current time = int(time.time()).
            score = i*500 - 1000 + int(time.time())
            test_dict = {
                "ID": box_id,
                "IP": "127.0.0.1",
                "PORT": 8000,
                "TYPE": "BOX",
                "COMMAND": "EXCHANGE"
            }
            self.redis.zadd(self.entrance._rk("BOX_SET"), score, box_id)
            self.redis.hmset(self.entrance._rk("EXCHANGE", box_id), test_dict)
        await asyncio.sleep(1.1)
        box_set_redis = self.redis.zrange(self.entrance._rk("BOX_SET"),
                                          start=0,
                                          end=int(time.time()) + 1000)
        # Only box-3 exists.
        self.assertEqual(box_set_redis, ['box-3'])
        for i in range(1, 3):
            self.assertFalse(self.redis.exists(self.entrance._rk("EXCHANGE", "box-{}".format(i))))
        self.assertTrue(self.redis.exists(self.entrance._rk("EXCHANGE", "box-3")))
