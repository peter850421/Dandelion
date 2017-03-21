import os
import random
import time
import subprocess
import logging
import redis
import configfile
from start_celery import app
from dandelion.httpclient import FileManager

try:
    import Queue as queue # version < 3.0
except ImportError:
    import queue

try:
    f = open("publisher-id.txt", 'r')
    publisher_id = f.read()
    f.close()
except IOError:
    raise Exception("Can't find publisher's id file")

logging.basicConfig(format='%(name)s %(asctime)s:\n %(message)s',
                    datefmt='%Y/%m/%d %H:%M:%S')

SERVER_IP           = configfile.SERVER_IP
SERVER_PORT         = configfile.SERVER_PORT
M3U8_WRITE_DIR      = configfile.M3U8_WRITE_DIR
M3U8_GET_DIR        = configfile.M3U8_GET_DIR
M3U8_READ_DIR       = configfile.M3U8_READ_DIR
MEDIA_GET_DIR       = configfile.MEDIA_GET_DIR
m3u8_media_amount   = configfile.M3U8_MEDIA_AMOUNT
expire_media_time   = configfile.EXPIRE_MEDIA_TIME
m3u8_time_waiting   = configfile.M3U8_TIME_WAITING
redis_ts_sorted_set = configfile.REDIS_EXPIRE_TS
REDIS_HOST          = configfile.REDIS_HOST


def logmsg(msg):
    logging.warning(msg)


def logwarning(msg):
    logging.error(msg)


@app.task
def mother_m3u8_modify(pathname):
###修改母m3u8資訊，存入box資料夾
    server_http_url     = "http://" + SERVER_IP + ":" + SERVER_PORT + "/"
    output_dir          = M3U8_WRITE_DIR + "/" + pathname.rsplit('/',1)[1]
    try:
        fp = open(pathname, "r+")
    except IOError:
        logwarning(' IOError in mother_m3u8_modify Pathname: %s.'%(pathname))
        return
    fp.seek(0)
    st = []
    line = fp.readline()
    # Read each line in file, modify lines and append it to list
    while line:
        if ".m3u8" in line:
            line = server_http_url + M3U8_GET_DIR + line
        st.append(line)
        line = fp.readline()

    if not os.path.exists(output_dir):
        outfile = open(output_dir, "w")
        outfile.close()
    outfile = open(output_dir, "r+")
    outfile.seek(0)
    for i in st:
        outfile.write(i)
    outfile.truncate()
    outfile.flush()
    outfile.close()
    logmsg("MODIFY MOTHER M3U8 %s." % pathname)

@app.task
def m3u8_trans(pathname, publisher_id):
    """
    -Read line from child m3u8
    """
    logmsg("M3U8_TRANS PATHNAME: %s"%(pathname))
    # Import from configfile

    # Connect to redis
    rdb = redis.StrictRedis(host=configfile.REDIS_HOST)
    # dir_name / stream_name / basename = XXX.mpd,
    #/tmp/hls/output/stream_name/xxx.m3u8
    path, basename = pathname.rsplit('/', 1)
    dir_name, stream_name = path.rsplit('/', 1)
    # m3u8 output path
    output_folder = os.path.join(M3U8_WRITE_DIR, stream_name)
    output_dir = os.path.join(output_folder, basename)
    # Open read file=>child.m3u8
    try:
        infile = open(pathname, "r")
    except IOError:
        logwarning('IOError in m3u8_trans() Pathname: %s.' % pathname)
        return
    # Check if the dir is created
    if not os.path.isdir(output_folder):
        subprocess.check_output(['mkdir', '-p', output_folder])
    # Open output file
    if not os.path.exists(output_dir):
        outfile = open(output_dir, "w")
        outfile.close()
    outfile = open(output_dir, "r+")
    outfile.seek(0)
    line = infile.readline()
    m = FileManager(publisher_id)
    lines_zadd = []
    while line:
        if '.ts' == line.rstrip()[-3:]:
            answer = m.ask(path+line)
            box_ip, box_port = (None, None)
            try:
                box_ip = answer['IP']
                box_port = answer['PORT']
            except KeyError:
                pass
            if box_ip is not None and box_port is not None:
                get_url_prefix = "http://"+box_ip+":"+box_port+"/"
                line = get_url_prefix + publisher_id + M3U8_READ_DIR + "/" + stream_name + "/" + line
            else:
                lines_zadd.append(line)
                get_url_prefix = "http://"+SERVER_IP+":"+SERVER_PORT+"/"
                line = get_url_prefix + MEDIA_GET_DIR + stream_name + "/" + line

        outfile.write(line)
        line = infile.readline()
    infile.close()
    outfile.truncate()
    outfile.flush()
    outfile.close()
    for line in lines_zadd:
        rdb.zadd(redis_ts_sorted_set, int(time.time()) + m3u8_time_waiting,
                 stream_name + "/" + line.rsplit('\n', 1)[0])


@app.task
def update_M3U8(ts_file, publisher_id):
    stream_name, ts      = ts_file.rsplit('/', 1)
    pathname            = M3U8_WRITE_DIR+'/'+stream_name+'/'+'index.m3u8'
    m = FileManager(publisher_id)
    box_ip = None
    box_port = None
    answer = m.ask(M3U8_READ_DIR + '/' + ts_file)
    try:
        box_ip=answer['IP']
        box_port=answer['PORT']
    except KeyError:
        logging.exception("Can't find IP or PORT in answer.", exc_info=False)
    if box_ip is None or box_port is None:
        return
    try:
        outfile = open(pathname, "r+")
    except IOError:
        logwarning('IOError in m3u8_trans() Pathname: %s.' % pathname)
        return
    outfile.seek(0)
    st = []
    line = outfile.readline()
    while line:
        if ts in line:
            if box_ip is not None and box_port is not None:
                line = line.rsplit("/", 1)[1]
                get_url_prefix = "http://"+box_ip+":"+box_port+"/"
                line = get_url_prefix + publisher_id + M3U8_READ_DIR + "/" + stream_name + "/" + line
        st.append(line)
        line = outfile.readline()
    outfile.seek(0)
    for i in st:
        outfile.write(i)
    outfile.truncate()
    outfile.flush()
    outfile.close()
    logging.info("Update %s" % ts)
    rdb = redis.StrictRedis(host=REDIS_HOST, decode_responses=True)
    rdb.zrem(redis_ts_sorted_set, ts_file)


### 檢查REDIS_TS_SORTED_SET 若ts對應box_id有值 則修改outfile_m3u8
def check_ts_sorted_set(publisher_id):
    # Connect to redis
    rdb = redis.StrictRedis(host=REDIS_HOST, decode_responses=True)
    #(redis_ts_sorted_set,TIME,stream_name + "/" + line)
    while True:
        ts_set = rdb.zrangebyscore(redis_ts_sorted_set, 0, 'inf', withscores=True)
        for ts, ts_score in ts_set:
            if ts_score < int(time.time()):
                rdb.zrem(redis_ts_sorted_set, ts)
            else:
                update_M3U8.delay(ts, publisher_id)
        time.sleep(0.001)
def recycle_expired_channel():
    logmsg ("Recycle Channel Process Start...")
    rdb = redis.StrictRedis(host=REDIS_HOST, decode_responses=True)
    while True:
        channel_set= rdb.zrangebyscore("channel_expire_set",0,int(time.time()))
        ### member = $channel_id_$id-$ip_$SHA1(client_id)
        for channel in channel_set:
            try:
                character=channel.find("-")
                rdb.srem(channel[0:character],channel[character+1:])
                logmsg ("Set:"+channel[0:character])
                rdb.zrem("channel_expire_set",channel)
                logmsg ("member:"+channel[character+1:]+"---Has Been Removed...")

            except Exception as e:
                logwarning('Expiring Error')
        time.sleep(2)
