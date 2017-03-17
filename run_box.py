import yaml
import uuid
from dandelion import Box


if __name__ == '__main__':
    # Get box id
    id = ''
    try:
        f = open("box-id.txt", "r")
        id = f.read()
        f.close()
    except IOError:
        pass
    if not id or id[:4] != "box-":
        id = "box-" + uuid.uuid4().hex
        f = open("box-id.txt", "w")
        f.write(id)
        f.close()
    # Load configfile
    f = open("dandelion.yaml", "r")
    config = yaml.safe_load(f)
    redis_address = (config["REDIS_HOST"],config["REDIS_PORT"])
    box = Box(id,
              ip=config["BOX_IP"],
              port=config["BOX_PORT"],
              entrance_urls=config["ENTRANCE_URLS"],
              redis_address=redis_address,
              redis_db=config["DB"],
              server_redis_minsize=config["SERVER_REDIS_MINSIZE"],
              server_redis_maxsize=config["SERVER_REDIS_MAXSIZE"],
              client_redis_minsize=config["CLIENT_REDIS_MINSIZE"],
              client_redis_maxsize=config["CLIENT_REDIS_MAXSIZE"],
              ping_entrance_freq=config["BOX_PING_ENTRANCE_FREQ"],
              base_directory=config["BASE_DIRECTORY"])
    box.start()


