import time
import os
import subprocess
from aiohttp import web, WSMsgType
from .utils import RedisKeyWrapper, filter_bytes_headers, ws_send_json
from .mysql_input import mysql_input, mysql_update_box

async def index(request):
    request.app["logger"].debug("trigger index!!")
    return web.Response(text="HI {0}".format(request.app["ID"]))


async def post(request):
    return web.Response(text="HI {0}".format(request.app["ID"]))


class BaseWebSocketHandler(object):
    """
    - Called by router to handle web socket request
    - Use dispatch() to handle different COMMANDs, if message's COMMAND is not defined,
      then on_DEFAULT will be fired
    """

    async def __call__(self, request):
        self.app = request.app
        self.id = self.app["ID"]
        self.rdp = self.app["redis_pool"]
        self.base_dir = None
        self.connect_id = None
        self.conf = self.app["conf"]
        self._rk = RedisKeyWrapper(self.id)
        self.logger = self.app["logger"]
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.app['websockets'].append(ws)
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    self.logger.debug(" RECEIVE MSG %s" % str(msg))
                    breakable = await self._dispatch(msg, ws, request)
                    if breakable:
                        break
                elif msg.type == WSMsgType.BINARY:
                    await self.on_BINARY(msg.data, ws, request)
                elif msg.type == WSMsgType.CLOSED:
                    break
                elif msg.type == WSMsgType.ERROR:
                    break
        except Exception as e:
            self.logger.exception("Something goes wrong in websockethandler...")
        finally:
            """
            If WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED occurs
            """
            self.app['websockets'].remove(ws)
        return ws

    async def _dispatch(self, msg, ws, request):
        try:
            load = msg.json()
            try:
                await self.assert_message_is_formal(load)
                command = str(load["COMMAND"])
            except (KeyError, ValueError) as e:
                await self.response_wrong_format(ws, load)
                return True
            try:
                return await getattr(self, "on_" + command, "on_DEFAULT")(load, ws, request)
            except Exception as e:
                self.logger.exception(e)
        except ValueError:
            self.logger.exception("Message is not valid JSON.")
        return True

    async def on_BINARY(self, msg, ws, request):
        pass

    async def on_DEFAULT(self, msg, ws, request):
        self.logger.debug("Fire on_DEFAULT !")
        return True

    async def ws_send(self, request, ws):
        self.logger.debug("ws_send(): %s" % (str(request)))
        await ws_send_json(request, ws, self.logger)

    @staticmethod
    async def assert_message_is_formal(msg):
        keys = ["ID", "IP", "PORT", "TYPE"]
        for k in keys:
            if k not in msg:
                if k == "PORT" and msg["TYPE"] == "PUBLISHER":
                    continue
                else:
                    raise KeyError("No key %s in received msg." % k)
            elif not msg[k]:
                raise ValueError("Value of key %s should not be empty or None" % k)

    async def get_own_info_dict(self):
        raise NotImplementedError()

    async def response_wrong_format(self, ws, msg):
        response = await self.get_own_info_dict()
        response["ERROR"] = "Wrong format in your message. Your message: %s" % (str(msg))
        await self.ws_send(response, ws)


class BoxWebSocketHandler(BaseWebSocketHandler):
    async def get_own_info_dict(self):
        return {
            "ID": self.id,
            "IP": self.app["IP"],
            "PORT": self.app["PORT"] if not self.app["PROXY_PORT"] else self.app["PROXY_PORT"],
            "TYPE": "BOX"
        }

    async def on_EXCHANGE(self, msg, ws, request):
        """ Mainly, exchanging both info
        - Store peer's message to redis and reply own box exchange message to peer
        """
        with await self.rdp as rdb:
            try:
                await rdb.hmset_dict(self._rk("EXCHANGE", msg["ID"]), msg)
            except:
                self.logger.exception("msg format is not valid dict")
            self_exchange = await rdb.hgetall(self._rk("SELF_EXCHANGE"))
            await self.ws_send(self_exchange, ws)
        return True

    async def on_PUBLISH(self, msg, ws, request):
        """
        This method should be invoked by publisher, which is searching for box to get available
        connections.
        """
        with await self.rdp as rdb:
            try:
                self.connect_id = msg["ID"]
                await rdb.hmset_dict(self._rk("EXCHANGE", self.connect_id), msg)
            except:
                self.logger.exception("msg format is not valid dict")
        # Create a path for publisher for later use.
        self.base_dir = os.path.join(self.conf["base_directory"], self.connect_id)
        if not os.path.isdir(self.base_dir):
            subprocess.check_output(['mkdir', '-p', self.base_dir])
        self.logger.info("Receive Connection from %s" % self.connect_id)
        response = await self.get_own_info_dict()
        response["MESSAGE"] = "ACCEPTED"
        response["COMMAND"] = "PUBLISH"
        await self.ws_send(response, ws)
        return False

    async def on_BINARY(self, msg, ws, request):
        """
        Receive binary message from publisher.
        1. Extract the msg into headers and file data
        2. store the file
        3. Store the file path to expire files set
        """
        headers, data = filter_bytes_headers(msg)
        try:
            file_path = headers["FILE_PATH"]
            # If any component is an absolute path, all previous components are thrown away
            if file_path[0] == '/':
                file_path = file_path[1:]
            file_path = os.path.join(self.base_dir, file_path)
            file_folder = os.path.dirname(file_path)
            if not os.path.isdir(file_folder):
                subprocess.check_output(['mkdir', '-p', file_folder])
            outfile = open(file_path, "wb")
            outfile.write(data)
            outfile.close()
            self.logger.info("Receive %s from %s" % (headers["FILE_PATH"], self.connect_id))
            try:
                ttl = int(headers["TTL"])
            except KeyError:
                ttl = 60
            if ttl:
                with await self.rdp as rdb:
                    await rdb.zadd(self._rk("EXPIRE_FILES"),
                                   int(time.time()) + ttl,
                                   file_path)
        except KeyError:
            self.logger.exception("No key 'FILE_PATH' in headers.")


class EntranceWebSocketHandler(BaseWebSocketHandler):
    async def get_own_info_dict(self):
        with await self.rdp as rdb:
            info = await rdb.hgetall(self._rk("OWN_INFO"))
            info["ENTRANCE_URLS"] = [self.app["ENTRANCE_URLS"]]
            others_entrance_urls = await rdb.smembers(self._rk("ENTRANCE_URLS"))
        for i in others_entrance_urls:
            info["ENTRANCE_URLS"].append(i)
        return info

    async def on_EXCHANGE(self, msg, ws, request):
        """
        Handle EXCHANGE request from boxes
        - Save exchange from the box in namespace (id):EXCHANGE:(box-exchange)
        - If the format is wrong, then send error message instead of saving it.
        """
        with await self.rdp as rdb:
            self.connect_id = msg["ID"]
            try:
                await rdb.hmset_dict(self._rk("EXCHANGE", self.connect_id), msg)
            except:
                self.logger.exception("msg is not valid dictionary")
            response = await self.get_own_info_dict()
            response["MESSAGE"] = "ACCEPTED"
            await self.ws_send(response, ws)
            await self.update_box(msg, rdb)
            await self.mysql_process_on_msg(msg)
            self.logger.info("Update box from %s on EXCHANGE" % self.connect_id)
        return True

    @staticmethod
    async def mysql_process_on_msg(msg):
        mysql_input(msg['ID'],
                    msg['IP'],
                    msg['PORT'],
                    msg['CPU-HZ'],
                    msg['CPU-NUM'],
                    msg['CPU-USR'],
                    msg['CPU-SYS'],
                    msg['CPU-NIC'],
                    msg['CPU-IDLE'],
                    msg['CPU-IO'],
                    msg['CPU-IRQ'],
                    msg['CPU-SIRQ'],
                    msg['LOADAVG-1'],
                    msg['LOADAVG-5'],
                    msg['LOADAVG-15'],
                    msg['MEM-TOTAL'],
                    msg['MEM-AVAIL'],
                    msg['DISK-TOTAL'],
                    msg['DISK-AVAIL'])
        mysql_update_box(msg['ID'],
                         msg['IP'],
                         msg['PORT'])

    async def update_box(self, msg, redis):
        """ Processing box's message by classifying it to proper set """
        await redis.zadd(self._rk("BOX_SET"),
                         int(time.time()) + self.conf["expire_box_time"],
                         self.connect_id)

    async def on_SEARCH(self, msg, ws, request):
        """Handle SEARCH request from publishers"""
        with await self.rdp as rdb:
            await self.response_to_publisher(msg, ws, rdb)
            self.logger.info("Receive Connection from %s on SEARCH" % msg["ID"])

    async def response_to_publisher(self, msg, ws, rdb):
        """
        - Get ENTRANCE SELF EXCHANGE
        - ADD available boxes from BOX_SET to response
        """
        response = await rdb.hgetall(self._rk("OWN_INFO"))
        response["COMMAND"] = "SEARCH"
        box_set_keys = await rdb.zrevrangebyscore(self._rk("BOX_SET"),
                                                  min=0,
                                                  offset=0,
                                                  count=self.conf["amount_of_boxes_per_request"])
        box_set = {}
        for box_id in box_set_keys:
            box_set[box_id] = await rdb.hgetall(self._rk("EXCHANGE", box_id))
        response["BOX_SET"] = box_set
        await self.ws_send(response, ws)
