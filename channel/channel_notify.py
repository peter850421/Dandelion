import pyinotify
import configfile
import redis
import asyncore
import multiprocessing
from server.tasks import logmsg, m3u8_trans, mother_m3u8_modify,check_ts_sorted_set
from dandelion.httpclient import FileManager

class EventHandler(pyinotify.ProcessEvent):
    def my_init(self, publisher_id, rdb):
        self.publisher_id = publisher_id
        self.rdb = rdb

    def process_IN_MOVED_TO(self, event):
        if "m3u8" != event.pathname[-4:]: return
        pre, post = event.pathname.rsplit('/', 1)
        if pre == configfile.M3U8_READ_DIR:
            ###modify mother m3u8
            mother_m3u8_modify.delay(event.pathname)
        else:
            """modify kid m3u8,if there is no box_ip then do nothing
            and put into REDIS_TS_SORTED_SET"""
            m3u8_trans.delay(event.pathname)
        logmsg("EventHandler process_IN_MOVED_TO: %s"%(event.pathname))

    def process_IN_CLOSE_WRITE(self, event):
        if ".ts" == event.pathname[-3:]:
            m = FileManager(self.publisher_id)
            m.push(event.pathname)
            logmsg("EventHandler process_IN_CLOSE_WRITE: %s" % event.pathname)


if __name__ == '__main__':
    try:
        f = open("publisher-id.txt", 'r')
        publisher_id = f.read()
        f.close()
    except IOError:
        raise Exception("Can't find publisher's id file")
    rdb        = redis.StrictRedis(host=configfile.REDIS_HOST)
    wm         = pyinotify.WatchManager() # Watch Manager
    mask       = pyinotify.IN_MOVED_TO | pyinotify.IN_CLOSE_WRITE
    handler    = EventHandler(rdb=rdb)
    notifier   = pyinotify.AsyncNotifier(wm, handler)
    wm.add_watch(configfile.M3U8_WATCH_PATH, mask, rec=True, auto_add=True)
    print("Notifier start loop...")
    check_ts_process = multiprocessing.Process(target=check_ts_sorted_set, args=())
    try:
        check_ts_process.start()
        asyncore.loop()
    except KeyboardInterrupt:
        check_ts_process.terminate()
        check_ts_process.join()
