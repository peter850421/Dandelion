import pymysql
import datetime
def mysql_input(IP,PORT,BOX_ID,CPU_NUM,CPU_LOADING,LOADING_AVG,Memory,DISK):
    mdb = pymysql.connect("localhost","root","elnj4j;3xj4","live_stream_db" )
    cursor = mdb.cursor()
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = "INSERT INTO `system`(`IP`, `PORT`, `BOX_ID`, `CPU_NUM`,\
     `CPU_LOADING`, `LOADING_AVG`, `Memory`, `DISK`, `time`) \
     VALUES (\'{ip}\', \'{port}\', \'{box_id}\', \'{cpu_num}\'\
     \'{cpu_loading}\', \'{loading_avg}\', \'{memory}\', \'{disk}\', \'{time0}\')".format(ip=IP,port=PORT,
                                                                    box_id=BOX_ID,
                                                                    cpu_num=CPU_NUM,
                                                                    cpu_loading=CPU_LOADING,
                                                                    loading_avg=LOADING_AVG,
                                                                    memory=Memory,
                                                                    disk=DISK,
                                                                    time0=Time0)
    try:
        cursor.execute(sql)
        mdb.commit()
    except:
       print ("Error: unable to fecth data")

    mdb.close()
