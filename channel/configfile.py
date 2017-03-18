### MPD Reading and Writing file directory
MPD_READ_DIR                = "/tmp/dash/output"
MPD_WRITE_DIR               = "/tmp/dash/media"
MPD_GET_DIR                 = "dash/media"   #no need to add '/' ahead
MPD_WATCH_PATH              = MPD_READ_DIR

### M3U8 Reading and Writing directory
M3U8_READ_DIR               = "/tmp/hls/output"
M3U8_WRITE_DIR              = "/tmp/hls/media"
M3U8_GET_DIR                = "hls/media/"
MEDIA_GET_DIR               = "hls/output/"
BOX_MEDIA_WRITE_DIR         = "/tmp/hls/output"
M3U8_WATCH_PATH             = M3U8_READ_DIR
M3U8_MEDIA_AMOUNT           = 12
M3U8_TIME_WAITING           = 1.0   #seconds (use float)

### ZMQ SETTINGS
# PUB-SUB MainTaining boxes' connections

# SERVER's HTTP Server IP PORT
SERVER_IP                   = "140.115.153.211"
SERVER_PORT                 = "8000"
MEDIA_BOX_UDPATE_DURATION   = 9   # Server will send it every    MEDIA_BOX_UDPATE_DURATION/3
SEND_MEDIA_QUEUE_NAME       = "SEND_MEDIA_QUEUE"

# Redis settings
REDIS_HOST                  = '127.0.0.1'
REDIS_BOX_SET               = "box_set"     # key
REDIS_BOX_MEDIA_AMOUNT      = "redis_box_media_amount"  #key
REDIS_TS_SORTED_SET         = "redis_ts_sorted_set"
EXPIRE_BOX_TIME             = 10
BOX_EXPIRE_MEDIA_TIME       = 60  # In box's redis
EXPIRE_MEDIA_TIME           = 60  # To expire media_path hash in server's redis
REDIS_EXPIRE_TS             = "REDIS_EXPIRE_TS"