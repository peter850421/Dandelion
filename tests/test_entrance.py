from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from dandelion.utils import create_id, RedisKeyWrapper
from dandelion.httpserver import EntranceAsyncServer
from dandelion.httpclient import PublisherAsyncClient
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
        super(BaseEntranceClientTestCase, self).tearDown()


class EntranceServerTestCase(BaseEntranceClientTestCase):
    async def get_application(self):
        await self.get_publisher()
        self.entrance = EntranceAsyncServer(id=self.id,
                                            ip="127.0.0.1",
                                            redis_db=2,
                                            port=8080,
                                            loop=self.loop,
                                            log_level=logging_level,
                                            amount_of_boxes_per_request=20)
        return self.entrance.app

    async def get_publisher(self):
        self.publisher = PublisherAsyncClient(id=create_id("publisher"),
                                              ip="127.0.0.1",
                                              loop=self.loop,
                                              redis_db=2,
                                              log_level=logging_level)
        await self.publisher.setup_aioredis()

    def tearDown(self):
        self.loop.run_until_complete(self.publisher.cleanup())
        super(EntranceServerTestCase, self).tearDown()

    @unittest_run_loop
    async def test_send_SEARCH_to_entrance(self):
        box_list = list()
        _rk = RedisKeyWrapper(self.entrance.id)
        for i in range(0, 30):
            data = {
                "ID": "box-{}".format(str(i)),
                "IP": "127.0.0.1",
                "PORT": 8080,
                "TYPE": "BOX"
            }
            box_list.append(int(time.time())+random.randint(0, 100))
            box_list.append(data["ID"])
            self.redis.hmset(_rk("EXCHANGE", data["ID"]), data)
        self.redis.zadd(_rk("BOX_SET"), *box_list)
        ws = await self.client.ws_connect(self.entrance.ws_url())
        await self.publisher.send_entrance(ws)
        response = await ws.receive()
        response = response.json()
        # Make sure that entrance returns 20 boxes
        self.assertEqual(len(response["BOX_SET"]), 20)
        # Throw the received message to on_SEARCH
        await self.publisher.on_SEARCH(response, ws)
        for box_id in response["BOX_SET"].keys():
            self.assertIn("box-", response["BOX_SET"][box_id]["ID"])
            # Comfirm that on_SEARCH has stored the BOX_SET into redis correctly
            self.assertTrue(self.redis.exists(self.publisher._rk("SEARCH", box_id)))