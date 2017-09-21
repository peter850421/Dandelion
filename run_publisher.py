import uuid
import yaml
import os
from dandelion import Publisher


if __name__ == '__main__':
    ROOT_DIR = os.environ["ROOT_DIR"] = os.path.dirname(__file__)
    id = ''
    try:
        f = open("publisher-id.txt", "r")
        id = f.read()
        f.close()
    except IOError:
        pass
    if not id or "publisher-" not in id:
        id = "publisher-" + uuid.uuid4().hex
        f = open(os.path.join(ROOT_DIR, "publisher-id.txt"), "w")
        f.write(id)
        f.close()
    print("Your ID: %s" % id)
    f = open(os.path.join(ROOT_DIR, "config.yaml"), "r")
    config = yaml.safe_load(f)
    redis_address = (config["REDIS_HOST"], config["REDIS_PORT"])
    publisher = Publisher(id,
                          ip=config["PUBLISHER_IP"],
                          entrance_urls=config["ENTRANCE_URLS"],
                          min_http_peers=config["MIN_HTTP_PEERS"],
                          redis_address=redis_address,
                          redis_db=config["DB"],
                          redis_maxsize=config["PUBLISHER_REDIS_MAXSIZE"],
                          redis_minsize=config["PUBLISHER_REDIS_MINSIZE"],
                          ping_entrance_freq=config["PUBLISHER_PING_ENTRANCE_FREQ"]
                          )
    publisher.start()

