import uuid
import yaml
from dandelion import Publisher


if __name__ == '__main__':
    id = ''
    try:
        f = open("publisher-id.txt", "r")
        id = f.read()
        f.close()
    except IOError:
        pass
    if not id or "publisher-" not in id:
        id = "publisher-" + uuid.uuid4().hex
        f = open("publisher-id.txt", "w")
        f.write(id)
        f.close()
    f = open("dandelion.yaml", "r")
    config = yaml.safe_load(f)
    redis_address = (config["REDIS_HOST"], config["REDIS_PORT"])
    publisher = Publisher(id,
                          ip=config["PUBLISHER_IP"],
                          port=config["PUBLISHER_PORT"],
                          entrance_urls=config["ENTRANCE_URLS"],
                          min_http_peers=config["MIN_HTTP_PEERS"],
                          redis_address=redis_address,
                          redis_db=config["DB"],
                          redis_maxsize=config["PUBLISHER_REDIS_MAXSIZE"],
                          redis_minsize=config["PUBLISHER_REDIS_MINSIZE"],
                          ping_entrance_freq=config["PUBLISHER_PING_ENTRANCE_FREQ"]
                          )
    publisher.start()

