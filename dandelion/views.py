import time
import os
import subprocess
from aiohttp import web, WSMsgType
from .utils import RedisKeyWrapper
from .utils import filter_bytes_headers
from .mysql_input import mysql_input,mysql_update_box

async def index(request):
    request.app["logger"].debug("trigger index!!")
    return web.Response(text="HI {0}".format(request.app["ID"]))


async def post(request):
    print(request.headers)
    return web.Response(text="HI {0}".format(request.app["ID"]))


class BaseWebSocketHandler(object):
    """
    - Called by router to handle web socket request
    - Use dispatch() to handle different COMMANDs, if message's COMMAND is not defined,
      then on_DEFAULT will be fired
    """

    async def __call__(self, request):
        self.id = request.app["ID"]
        self.rdp = request.app["redis_pool"]
        self.base_dir = None
        self.connect_id = None
        self.conf = request.app["conf"]
        self._rk = RedisKeyWrapper(self.id)
        self.logger = request.app["logger"]
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        request.app['websockets'].append(ws)
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
            request.app['websockets'].remove(ws)
        return ws

    async def _dispatch(self, msg, ws, request):
        try:
            load = msg.json()
            try:
                command = str(load["COMMAND"])
                return await getattr(self, "on_" + command, "on_DEFAULT")(load, ws, request)
            except KeyError:
                self.logger.exception("No COMMAND key in msg.")
                await self.on_DEFAULT(msg, ws, request)
        except ValueError:
            self.logger.exception("Message is not valid JSON.")
        return True

    async def on_BINARY(self, msg, ws, request):
        pass

    async def on_DEFAULT(self, msg, ws, request):
        self.logger.debug("Fire on_DEFAULT !")
        return True

    async def ws_send(self, request, ws):
        self.logger.debug(" ws_send(): %s" % (str(request)))
        try:
            ws.send_json(request)
        except ValueError:
            self.logger.exception("Could not serialize request.")
        except (RuntimeError, TypeError):
            self.logger.exception("Could not send_json().")


class BoxWebSocketHandler(BaseWebSocketHandler):
    async def on_EXCHANGE(self, msg, ws, request):
        """
        - Store peer's message to redis and send own exchange message to peer
        """
        keys = ["ID", "IP", "PORT", "TYPE"]
        if not all(key in msg.keys() for key in keys):
            self.logger.debug("Wrong EXCHANGE format")
        with await self.rdp as rdb:
            try:
                await rdb.hmset_dict(self._rk("EXCHANGE", msg["ID"]), msg)
            except:
                self.logger.exception("msg format is not valid dict")
            self_exchange = await rdb.hgetall(self._rk("SELF_EXCHANGE"))
            await self.ws_send(self_exchange, ws)
        return True

    async def on_PUBLISH(self, msg, ws, request):
        keys = ["ID", "IP", "PORT", "TYPE"]
        if not all(key in msg.keys() for key in keys):
            self.logger.debug("Wrong PUBLISH format")
            return True
        with await self.rdp as rdb:
            try:
                self.connect_id = msg["ID"]
                await rdb.hmset_dict(self._rk("EXCHANGE", self.connect_id), msg)
            except:
                self.logger.exception("msg format is not valid dict")
        self.base_dir = os.path.join(self.conf["base_directory"], self.connect_id)
        if not os.path.isdir(self.base_dir):
            subprocess.check_output(['mkdir', '-p', self.base_dir])
        self.logger.info("Receive Connection from %s" % self.connect_id)
        return False

    async def on_BINARY(self, msg, ws, request):
        headers, data = filter_bytes_headers(msg)
        try:
            file_path = headers["FILE_PATH"]
            # If any component is an absolute path, all previous components are thrown away
            if file_path[0] == '/':
                file_path = file_path[1:]
            file_path = os.path.join(self.base_dir, file_path)
            file_folder = file_path.rsplit('/', 1)[0]
            if not os.path.isdir(file_folder):
                subprocess.check_output(['mkdir', '-p', file_folder])
            outfile = open(file_path, "wb")
            outfile.write(data)
            outfile.close()
            self.logger.info("Receive %s from %s" % (headers["FILE_PATH"], self.connect_id))
            try:
                ttl = int(headers["TTL"])
                if ttl:
                    with await self.rdp as rdb:
                        await rdb.zadd(self._rk("EXPIRE_FILES"),
                                       int(time.time()) + ttl,
                                       file_path)
            except KeyError:
                pass
        except KeyError:
            self.logger.exception("No key 'FILE_PATH' in headers.")


class EntranceWebSocketHandler(BaseWebSocketHandler):
    async def on_EXCHANGE(self, msg, ws, request):
        """
        Handle EXCHANGE request from boxes
        - Save exchange from the box in namespace (id):EXCHANGE:(box-exchange)
        - If the format is wrong, then send error message instead of saving it.
        """
        keys = ["ID", "IP", "PORT", "TYPE"]
        with await self.rdp as rdb:
            if not all(key in msg.keys() for key in keys):
                self.logger.debug("Wrong EXCHANGE format")
                await self.response_to_box("Wrong EXCHANGE Format.", ws, rdb)
            else:
                self.connect_id = msg["ID"]
                try:
                    await rdb.hmset_dict(self._rk("EXCHANGE", self.connect_id), msg)
                except:
                    self.logger.exception("msg is not valid dictionary")
                await self.response_to_box("Accept", ws, rdb)
                await self.update_box(msg, rdb)
                self.logger.info("Receive Connection from %s on EXCHANGE" % self.connect_id)
                mysql_input(msg['ID'],
                            msg['IP'],
                            msg['PORT'],
                            msg['CPU-HZ'],
                            msg['CPU_NUM'],
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

                self.logger.info("Update box_info from %s on EXCHANGE" % self.connect_id)
                mysql_update_box(msg['ID'],
                                 msg['IP'],
                                 msg['PORT'])
                self.logger.info("Update box from %s on EXCHANGE" % self.connect_id)
        return True

    async def response_to_box(self, response_msg, ws, rdb):
        response = await rdb.hgetall(self._rk("OWN_INFO"))
        response["COMMAND"] = "EXCHANGE"
        response["MESSAGE"] = response_msg
        await self.ws_send(response, ws)

    async def update_box(self, msg, redis):
        """ Processing box's message by classifying it to proper set """
        await redis.zadd(self._rk("BOX_SET"),
                         int(time.time()) + self.conf["expire_box_time"],
                         self.connect_id)

    async def on_SEARCH(self, msg, ws, request):
        """Handle SEARCH request from publishers"""
        with await self.rdp as rdb:
            await self.response_to_publisher(msg, ws, rdb)
            try:
                self.logger.info("Receive Connection from %s on SEARCH" % msg["ID"])
            except KeyError:
                self.logger.exception("No Key ID in message on SEARCH")

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
