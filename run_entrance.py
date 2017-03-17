from dandelion import Entrance
import uuid
import yaml

if __name__ == '__main__':
    id = ''
    try:
        f = open("entrance-id.txt", "r")
        id = f.read()
        f.close()
    except IOError:
        pass
    if not id or "entrance-" not in id:
        id = "entrance-" + uuid.uuid4().hex
        f = open("entrance-id.txt", "w")
        f.write(id)
        f.close()
    f = open("dandelion.yaml", "r")
    config = yaml.safe_load(f)
    redis_address = (config["REDIS_HOST"], config["REDIS_PORT"])
    entrance = Entrance(id=id, ip=config["ENTRANCE_IP"], port=config["ENTRANCE_PORT"],
                        redis_address=redis_address,
                        redis_db=config["DB"],
                        redis_minsize=config["ENTRANCE_REDIS_MINSIZE"],
                        redis_maxsize=config["ENTRANCE_REDIS_MAXSIZE"],
                        expire_box_time=config["ENTRANCE_EXPIRE_BOX_TIME"],
                        amount_of_boxes_per_request=config["AMOUNT_OF_BOXES_PER_REQUEST"],
                        )
    entrance.serve_forever()
