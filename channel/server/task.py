import os
import random
import time
import subprocess
import logging
import redis
import configfile
from start_celery import app
try:
    import Queue as queue # version < 3.0
except ImportError:
    import queue

def logmsg(msg):
    logging.basicConfig(format='%(name)s %(asctime)s:\n %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S')
    logging.warning(msg)

def logwarning(msg):
    logging.basicConfig(format='%(name)s %(asctime)s:\n %(message)s',
                        datefmt='%Y/%m/%d %H:%M:%S')
    logging.error(msg)

@app.task
def mother_m3u8_modify(pathname):
###修改母m3u8資訊，存入box資料夾
    SERVER_IP           = configfile.SERVER_IP
    SERVER_PORT         = configfile.SERVER_PORT
    M3U8_WRITE_DIR      = configfile.M3U8_WRITE_DIR
    M3U8_GET_DIR        = configfile.M3U8_GET_DIR
    server_http_url     = "http://" + SERVER_IP + ":" + SERVER_PORT + "/"
    output_dir          = configfile.M3U8_WRITE_DIR + "/" + pathname.rsplit('/',1)[1]
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
    logmsg("MODIFY MOTHER M3U8 %s."%(pathname))
@app.task
def m3u8_trans(pathname):
    """
    -Read line from child m3u8
    """
    logmsg("M3U8_TRANS PATHNAME: %s"%(pathname))
    # Import from configfile
    M3U8_WRITE_DIR      = configfile.M3U8_WRITE_DIR
    MEDIA_GET_DIR       = configfile.MEDIA_GET_DIR
    m3u8_media_amount   = configfile.M3U8_MEDIA_AMOUNT
    SERVER_IP           = configfile.SERVER_IP
    SERVER_PORT         = configfile.SERVER_PORT
    expire_media_time   = configfile.EXPIRE_MEDIA_TIME
    m3u8_time_waiting   = configfile.M3U8_TIME_WAITING
    redis_ts_sorted_set = configfile.REDIS_EXPIRE_TS
    # Connect to redis
    rdb = redis.StrictRedis(host=configfile.REDIS_HOST)
    # dir_name / stream_name / basename = XXX.mpd,
    #/tmp/hls/output/stream_name/xxx.m3u8
    path, basename = pathname.rsplit('/', 1)
    dir_name, stream_name = path.rsplit('/', 1)
    # Open read file=>child.m3u8
    try:
        infile = open(pathname, "r")
    except IOError:
        logwarning('IOError in m3u8_trans() Pathname: %s.'%(pathname))
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
    while line:
        if '.ts' == line.rstrip()[-3:]:
            box_ip="123"
            box_port="123"
            if box_ip != None and box_por != None:
                get_url_prefix = "http://"+box_ip+":"+box_port+"/"
                line = get_url_prefix + MEDIA_GET_DIR + stream_name + "/" + line
            else:
                #get_url_prefix = "http://"+SERVER_IP+":"+SERVER_PORT+"/"
                #line = get_url_prefix + MEDIA_GET_DIR + stream_name + "/" + line
                rdb.zadd(redis_ts_sorted_set,int(time.time())+m3u8_time_waiting,stream_name + "/" + line)
        outfile.write(line)
        line = infile.readline()
    infile.close()
    outfile.truncate()
    outfile.close()
@app.task
def update_M3U8(ts_file):
    # Import from configfile
    M3U8_WRITE_DIR      = configfile.M3U8_WRITE_DIR
    pathname            = M3U8_WRITE_DIR+ts_file
    try:
        outfile = open(pathname, "r+")
    except IOError:
        logwarning('IOError in m3u8_trans() Pathname: %s.'%(pathname))
        return
    outfile.seek(0)
    line.outfile.readline()
    while line:
        if '.ts' == line.rstrip()[-3:]:
            box_ip="123"
            box_port="123"
            if box_ip != None and box_por != None:
                get_url_prefix = "http://"+box_ip+":"+box_port+"/"
                line = get_url_prefix + MEDIA_GET_DIR + stream_name + "/" + line

        outfile.write(line)
        line = outfile.readline()
    outfile.truncate()
    outfile.close()

### 檢查REDIS_TS_SORTED_SET 若ts對應box_id有值 則修改outfile_m3u8
def check_ts_sorted_set:
    redis_ts_sorted_set = configfile.REDIS_EXPIRE_TS
    # Connect to redis
    rdb = redis.StrictRedis(host=configfile.REDIS_HOST)
    #(redis_ts_sorted_set,TIME,stream_name + "/" + line)
    while True:
        ts_set = rdb.zrangebyscore(redis_ts_sorted_set,0,+inf)
        for ts in ts_set:
            update_M3U8.delay(ts)
            ts_score = rdb.zscore(redis_ts_sorted_set,ts)
            if ts_score<int(time.time()):
                rdb.zrem("channel_expire_set",ts)
