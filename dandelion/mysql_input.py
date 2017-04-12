import pymysql
import datetime
def mysql_input(IP,PORT,BOX_ID,CPU_NUM,CPU_LOADING,LOADING_AVG,Memory,DISK):
    mdb = pymysql.connect("localhost","root","elnj4j;3xj4","live_stream_db" )
    cursor = mdb.cursor()
    time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = "INSERT INTO `system`(`IP`, `PORT`, `BOX_ID`, `CPU_NUM`,\
     `CPU_LOADING`, `LOADING_AVG`, `Memory`, `DISK`, `time`) \
     VALUES ({IP}, {PORT}, {BOX_ID}, {CPU_NUM}\
     {CPU_LOADING}, {LOADING_AVG}, {Memory}, {DISK}\'{time0}\')".format(IP=IP,PORT=PORT,
                                                                    BOX_ID=BOX_ID,
                                                                    CPU_NUM=CPU_NUM,
                                                                    CPU_LOADING=CPU_LOADING,
                                                                    LOADING_AVG=LOADING_AVG,
                                                                    Memory=Memory,
                                                                    DISK=DISK,
                                                                    time0=time0)
    try:
        cursor.execute(sql)
        mdb.commit()
    except:
       print ("Error: unable to fecth data")

    mdb.close()
