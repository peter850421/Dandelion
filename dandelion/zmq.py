import time
import os
import subprocess
import zmq
import zmq.asyncio
import asyncio
import logging
import uvloop
import aioredis
import redis
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from .utils import RedisKeyWrapper
from .utils import redis_key_wrap as rkwrap
from .logger import get_logger


"""

- {ID}:ZMQ:{FILE PATH}
    - {"VERIFY": True/False,
       "BOX_ID": {box id}
      }
- {ID}:ZMQ:BOX_LIST  (list, for sending file process to pick a box)
- {ID}:ZMQ:EXPIRE_SET (sorted set, score=time, value=box id)
- {ID}:ZMQ:FILE_PATH_QUEUE (list, for api to push file path into it)
- {ID}:ZMQ:PROCESSED_FILES:(FILE_PATH)  (hash, to store file that have sent)

##ZMQ TOPIC
- ping topic: ZMQ_PING_TOPIC
- verify topic: ZMQ_VERIFY_TOPIC


"""

class AsyncZMQServer(object):
    def __init__(self, id,
                 zmq_xsub_address,
                 collecting_address,
                 sending_processes_num=3,
                 zmq_expire_box_time=30,
                 loop=None,
                 log_level=logging.DEBUG,
                 ctx=None,
                 redis_address=("localhost", 6379),
                 redis_db=0):
        self.id = id
        self.sending_processes_num = sending_processes_num
        self.expire_time = zmq_expire_box_time
        self.ctx = zmq.asyncio.Context() if not ctx else ctx
        self._send_processes = []
        self._loop = zmq.asyncio.ZMQEventLoop() if not loop else loop
        asyncio.set_event_loop(self._loop)
        self._rk = RedisKeyWrapper(self.id + ":ZMQ")
        self.logger = get_logger("AsyncZMQServer", level=log_level)
        self.conf = {"zmq_xsub_address": zmq_xsub_address,
                     "redis_address": redis_address,
                     "redis_db": redis_db,
                     "collecting_address": collecting_address}
        self._loop.run_until_complete(asyncio.gather(self.setup()))

    @property
    def loop(self):
        return self._loop

    async def setup(self):
        self.rdb = await aioredis.create_redis(self.conf["redis_address"],
                                               db=self.conf["redis_db"])

    def start(self):
        """
        - Start multiple ZMQ sending processes and append the processes to the list
        - Start ZMQ collecting process
        """
        for i in range(self.sending_processes_num):
            p = ZMQSendingProcess(i, self.id,
                                  logger=self.logger,
                                  zmq_xsub_address=self.conf["zmq_xsub_address"],
                                  redis_address=self.conf["redis_address"],
                                  redis_db=self.conf["redis_db"])
            p.start()
            self._send_processes.append(p)
        asyncio.ensure_future(self.update_box_set())
        asyncio.ensure_future(self.collecting_process())
        try:
            self.logger.info("AsyncZMQServer start...")
            self._loop.run_forever()
        except KeyboardInterrupt:
            self.logger.exception("KeyboardInterrupt.")
        finally:
            self.ctx.destroy()
            for p in self._send_processes:
                p.terminate()
                p.join()
        self.logger.info("AsyncZMQServer stops.")

    async def update_box_set(self):
        while True:
            now = int(time.time())
            box_list = await self.rdb.zrangebyscore(self._rk("EXPIRE_SET"), min=0,
                                                    max=now)
            if box_list:
                for item in box_list:
                    await self.rdb.lrem(self._rk("BOX_LIST"), 1, item)

                await self.rdb.zrem(self._rk("EXPIRE_SET"), *box_list)
            await asyncio.sleep(2)

    async def collecting_process(self):
        """
        - Create subscribe socket
        - Receive Message from boxes
        - Message could be two topic, "ZMQ_PING_TOPIC" and "ZMQ_VERIFY_TOPIC"
        :return:
        """
        sub_sock = self.ctx.socket(zmq.SUB)
        sub_sock.bind(self.conf["collecting_address"])
        sub_sock.setsockopt(zmq.SUBSCRIBE, "ZMQ_VERIFY_TOPIC".encode())
        sub_sock.setsockopt(zmq.SUBSCRIBE, "ZMQ_PING_TOPIC".encode())
        await asyncio.sleep(1)
        self.logger.info("AsyncZMQServer Collecting Process start...")
        while True:
            data = await sub_sock.recv_multipart()
            for i in range(len(data)):
                data[i] = data[i].decode()
            if data[0] == "ZMQ_PING_TOPIC":
                await self.process_ping_topic(data)
            elif data[0] == "ZMQ_VERIFY_TOPIC":
                await self.process_verify_data(data)

    async def process_verify_data(self, data):
        """
        data = ["ZMQ_VERIFY TOPIC", FILE_PATH, BOX ID ]
        """
        await self.rdb.hmset(self._rk("PROCESSED_FILES", data[1]), "BOX_ID", data[2])
        self.logger.info(" VERIFY %s by %s." % (data[1], data[2]))

    async def process_ping_topic(self, data):
        """
        - data = [ "ZMQ_PING_TOPIC", BOX_ID ]
        - Push the box to BOX_LIST, if the box doesn't exist in it
        - Update the status of the box in EXPIRE_SET
        """
        exist = await self.rdb.zrank(self._rk("EXPIRE_SET"), data[1])
        if not exist:
            await self.rdb.rpush(self._rk("BOX_LIST"), data[1])
        await self.rdb.zadd(self._rk("EXPIRE_SET"), int(time.time()) + self.expire_time, data[1])
        self.logger.info(" PING from %s." % (data[1]))



class ZMQSendingProcess(multiprocessing.Process):
    def __init__(self, num, id, logger, zmq_xsub_address,
                 redis_address=("localhost", 6379),
                 redis_db=0):
        multiprocessing.Process.__init__(self)
        self.num = num
        self.id = id
        self._rk = RedisKeyWrapper(self.id + ":ZMQ")
        self.logger = logger
        self.zmq_xsub_address = zmq_xsub_address
        self.redis_address = redis_address
        self.redis_db = redis_db

    def run(self):
        """
        - Create ZMQ Context and Publish Socket
        - Pop up from queue to get the task (blocking)
        - Read file
        - Send File
        - Save the dictionary of file to redis, file path as key and two fields
        :return:
        """
        ctx = zmq.Context()
        pub_sock = ctx.socket(zmq.PUB)
        pub_sock.connect(self.zmq_xsub_address)
        time.sleep(1)
        rdb = redis.StrictRedis(host=self.redis_address[0], port=self.redis_address[1],
                                db=self.redis_db)
        logging.info("AsyncZMQServer %d Sending Process start..." % (self.num))
        while True:
            msg = ''
            box = self.pick_box(rdb, amount=1)
            if not box:
                self.logger.warning("No available boxes for zmq to send.")
            else:
                file_path = str(rdb.blpop(self._rk("FILE_PATH_QUEUE"))[0])
                try:
                    infile = open(file_path, "rb")
                    data = [box.encode(), file_path.encode(), infile.read()]
                    pub_sock.send_multipart(data)
                    logging.debug(" SEND %s to %s" % (file_path, box))
                    msg = "SENT"
                except IOError:
                    self.logger.exception("No such file %s" % file_path)
                    msg = 'NO SUCH FILE'
                save_dict = {
                    "VERIFY": False,
                    "BOX_ID": box,
                    "MSG": msg,
                }
                rdb.hmset(self._rk("PROCESSED_FILES", file_path), save_dict)

    def pick_box(self, rdb, amount=1, timeout=1):
        """Pop boxes from the head of list and push them back to the tail"""
        box_list = []
        for i in range(amount):
            box_list.append(rdb.blpop(self._rk("BOX_LIST"),
                                      timeout=timeout))
            if not box_list:
                return None
        rdb.rpush(self._rk("BOX_LIST"), box_list)
        if amount == 1:
            return box_list[0]
        return box_list


class QueueManager(object):
    """
    This class is an api for other users to connect to AsyncZMQServer. The basic usage for now is that
    users should push their file's name or directory, (assuming that user's process and AsyncZMQServer
    are running  on the same machine, so that we could read the file locally by provided file's
    directory)to the queue, and then our zmq server would get the file name and assign a box to that
    file. Once the file is sent, users could check if the file is assigned to which box via this
    manager.
    Future development:
    - Users could send their files via network instead of local machine.
    - This manager should also combine http server's feature to send file through http
    """
    def __init__(self, id,
                 redis_address=("localhost", 6379),
                 redis_db=0, ):
        self.id = id
        self.rdb = redis.StrictRedis(host=redis_address[0],
                                     port=redis_address[1],
                                     db=redis_db)
        self._rk = RedisKeyWrapper(self.id + ":ZMQ")

    def push(self, filename):
        assert(isinstance(filename, str))
        self.rdb.rpush(self._rk("FILE_PATH_QUEUE"), filename)

    def ask(self, filename):
        """
        :param filename:  file's directory
        :return: dictionary of the filename in redis, if not exist then return none
        """
        return self.rdb.hgetall(self._rk("PROCESSED_FILES", filename))



class AsyncZMQBox(object):
    def __init__(self, id,
                 base_dir="/tmp",
                 max_subscribes=4,
                 redis_address=("localhost", 6379),
                 redis_db=0,
                 log_level=logging.DEBUG):
        self.id = id
        self.max_subscribes = max_subscribes
        self._loop = uvloop.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._rk = RedisKeyWrapper(self.id + ":ZMQ")
        self.logger = get_logger("AsyncZMQBox", level=log_level)
        self.conf = {"redis_address": redis_address,
                     "redis_db": redis_db,
                     "base_dir": base_dir,
                     }
        self.subscribing_process = {}
        self.executor = ThreadPoolExecutor(max_workers=max_subscribes)

        async def setup():
            return await aioredis.create_redis(self.conf["redis_address"],
                                        db=self.conf["redis_db"],
                                        encoding="utf-8")

        self.rdb = self._loop.run_until_complete(asyncio.ensure_future(setup()))

    @property
    def loop(self):
        return self._loop


    def start(self):
        asyncio.ensure_future(self.run())
        try:
            self.logger.info(" AsyncZMQBox start...")
            self.loop.run_forever()
        except KeyboardInterrupt:
            logging.exception(" KeyboardInterrupt.")
        self.loop.close()
        self.logger.info(" AsyncZMQBox stops.")

    async def run(self):
        """
        - Look up PUBLISHER_SET to see if new publisher comes in
        - Make sure that max subscription should not be more than max_subscribes
        - Subscribe
        :return:
        """
        self.logger.info("AsyncZMQBox start running...")
        while True:
            publishers = await self.rdb.smembers(self._rk("PUBLISHER_SET"))
            subscribing_num = await self.rdb.scard(self._rk("SUBSCRIBING"))
            for publisher in publishers:
                if subscribing_num <= self.max_subscribes and \
                not publisher in self.subscribing_process:
                        self.subscribing_process[publisher] = asyncio.ensure_future(self.subscribe(publisher))
                        await self.rdb.sadd(self._rk("SUBSCRIBING"), publisher)
            for item in self.subscribing_process.keys():
                if self.subscribing_process[item].done():
                    self.subscribing_process.pop(item)
                    await self.rdb.srem(self._rk("SUBSCRIBING"), item)
            await asyncio.sleep(3)

    async def subscribe(self, publisher):
        await self.loop.run_in_executor(self.executor,
                                        subscribe,
                                        self.id,
                                        publisher,
                                        self.conf,
                                        self.logger)


def subscribe(id, publisher, conf, logger):
    """
    - Create pub and sub sockets
    - Create two tasks, receiving and pinging process
    """
    loop = zmq.asyncio.ZMQEventLoop()
    ctx = zmq.asyncio.Context()
    asyncio.set_event_loop(loop)
    _rk = RedisKeyWrapper(id + ":ZMQ")


    rdb = redis.StrictRedis(host=conf["redis_address"][0], port=conf["redis_address"][1],
                                db=conf["redis_db"])
    try:
        ping_address = (rdb.hmget(rkwrap(id, "SUBSCRIBE", publisher),
                        "ZMQ_PING_ADDRESS"))[0]
        receive_address = (rdb.hmget(rkwrap(id, "SUBSCRIBE", publisher),
                                 "ZMQ_RECEIVE_ADDRESS"))[0]
        print(ping_address, receive_address)
    except KeyError:
        if (ping_address == [None]) or (receive_address == [None]):
            rdb.delete(rkwrap(id, "SUBSCRIBE", publisher))
            rdb.srem(_rk("PUBLISHER_SET"), publisher)
            logger.warning("%s has no ZMQ_PING_ADDRESS or ZMQ_RECEIVE_ADDRESS data" % publisher)
            return


    pub_sock = ctx.socket(zmq.PUB)
    pub_sock.connect(ping_address)
    sub_sock = ctx.socket(zmq.SUB)
    sub_sock.setsockopt(zmq.SUBSCRIBE, id.encode())
    sub_sock.connect(receive_address)

    tasks = [
        asyncio.ensure_future(ping_process(id, publisher, pub_sock, sub_sock, conf, logger)),
        asyncio.ensure_future(receiving_process(id, publisher, pub_sock, sub_sock, conf, logger))
    ]
    logger.info("Start to subscribing publisher: %s." % publisher)
    loop.run_until_complete(asyncio.gather(*tasks))
    rdb.srem(_rk("SUBSCRIBING"), publisher)
    return


async def receiving_process(id, publisher, pub_sock, sub_sock, conf, logger):
    """
    - Use publisher's id as folder's name under base_dir
    - wait for data to arrive
    - decode data
    - make file's dir
    - write file
    - send verify back to publisher
    """
    await asyncio.sleep(1)
    output_dir = os.path.join(conf["base_dir"], publisher)
    if not os.path.isdir(output_dir):
        subprocess.check_output(['mkdir', '-p', output_dir])
    while not sub_sock.closed:
        data = await sub_sock.recv_multipart()
        for i in range(len(data) - 1):
            data[i] = data[i].decode()
        data_dir = os.path.join(output_dir, data[1])
        folder, file_name = data_dir.rsplit('/', 1)
        folder_dir = os.path.join(output_dir, folder)
        if not os.path.isdir(folder_dir):
            subprocess.check_output(['mkdir', '-p', folder_dir])
        # Write to file
        outfile = open(os.path.join(folder_dir, file_name), "wb")
        outfile.write(data[2])
        outfile.flush()
        outfile.close()
        # Verify
        verify_data = ["ZMQ_VERIFY_TOPIC", data[1], id]
        for i in range(len(verify_data)):
            verify_data[i] = verify_data[i].encode()
        await pub_sock.send_multipart(verify_data)
        logger.info("RECEIVE %s" % data[1])
    pub_sock.close()
    logger.warning("%s socket close." % (publisher))


async def ping_process(id, publisher, pub_sock, sub_sock, conf, logger):
    await asyncio.sleep(1)
    while not pub_sock.closed:
        await pub_sock.send_multipart(["ZMQ_PING_TOPIC".encode(), id.encode()])
        await asyncio.sleep(3)
    sub_sock.close()
    logger.warning("%s socket close." % (publisher))

