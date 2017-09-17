import aiohttp
import json
import uuid

GET_IP_URL = [
              'http://bot.whatismyipaddress.com',
              'http://icanhazip.com',
              'http://ipecho.net/plain',
              # 'https://api.ipify.org',
              # 'https://myexternalip.com/raw',
              # 'https://ifconfig.co/ip',
              ]

url_geo = [
    "http://ip-api.com/json",
    'http://ipinfo.io/json'
]


def create_id(prefix):
    return "{0}-{1}".format(prefix, uuid.uuid4().hex)


def redis_key_wrap(*args):
    if len(args) == 0: return
    s = ''
    for i in range(len(args)):
        if i == 0 and args[i]:
            s = str(args[i])
        else:
            s = s + ":" + str(args[i])
    return s

class RedisKeyWrapper:
    def __init__(self, *args):
        self._bn = self.wrap(*args)

    def __call__(self, *args):
        if not len(args): return self._bn
        return self.wrap(self._bn, *args)

    def wrap(self, *args):
        s = ''
        for i in range(len(args)):
            if not isinstance(args[i], str):
                raise TypeError("Arguments should be <type 'str'>")
            if i == 0:
                s = args[i]
            elif args[i] is not '':
                s = s + ":" + args[i]
        if len(s) > 0 and s[0] == ":":
            s = s[1:]
        return s

    def __str__(self):
        return self._bn


async def geoip_fetch():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://ipinfo.io/json') as resp:
            return await resp.json()


class URLWrapper:
    def __init__(self, base_url):
        if base_url[-1] != "/":
            base_url += '/'
        self.base_url = base_url

    def __call__(self, *args):
        if not len(args): return self.base_url
        url = self.base_url
        for i in range(len(args)):
            item = args[i]
            assert (isinstance(item, str))
            if item == '/': continue
            if item[0] == '/':
                item = item[1:]
            if item[-1] == '/':
                item = item[:-1]
            if i == len(args) - 1:
                url += item
            else:
                url = url + item + "/"
        return url


def get_key_tail(key):
    return key.rsplit(":", 1)[-1]

def wrap_bytes_headers(headers):
    """
    - json dumps dicts
    - encode to bytes
    - wrap with self defined block
    :param headers: dictionary
    :return: bytes
    """
    b_hdrs = json.dumps(headers).encode("utf-8")
    return b'<Dandelion>'+b_hdrs+b'</Dandelion>'

def filter_bytes_headers(message):
    headers, data = message.split(b"</Dandelion>", 1)
    headers = json.loads(headers.split(b"<Dandelion>")[1].decode("utf-8"))
    return headers, data

async def get_ip():
    ip = None
    for url in GET_IP_URL:
        try:
            async with aiohttp.ClientSession(read_timeout=10, conn_timeout=10) as session:
                async with session.get(url) as resp:
                    ip = str(await resp.text()).replace('\n', '')
            if len(ip.split('.')) == 4:
                return ip
        except:
            pass
    return ip
