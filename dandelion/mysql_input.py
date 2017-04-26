import pymysql
import datetime
def mysql_input(BOX_ID,IP,PORT,CPU_HZ,CPU_NUM,CPU_USR,CPU_SYS,CPU_NIC,
                CPU_IDLE,CPU_IO,CPU_IRQ,CPU_SIRQ,LOADAVG_1,LOADAVG_5,
                LOADAVG_15,MEM_TOTAL,MEM_AVAIL,DISK_TOTAL,DISK_AVAIL):
    mdb = pymysql.connect("localhost","root","elnj4j;3xj4","live_stream_db" )
    cursor = mdb.cursor()
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = "INSERT INTO `box_info`(`box-id`, `ip`, `port`, `cpu-Hz`, `cpu-num`, `cpu-usr`, \
     `cpu-sys`, `cpu-nic`, `cpu-idle`, `cpu-io`, `cpu-irq`, `cpu-sirq`, `loadavg-1`, `loadavg-5`, \
     `loadavg-15`, `mem-total`, `mem-avail`, `disk-total`, `disk-avail`,`time`) \
     VALUES (\"{box_id}\", \"{ip}\", \"{port}\", \"{cpu_Hz}\", \"{cpu_num}\", \"{cpu_usr}\", \
     \"{cpu_sys}\", \"{cpu_nic}\", \"{cpu_idle}\", \"{cpu_io}\", \"{cpu_irq}\", \"{cpu_sirq}\", \"{loadavg_1}\", \"{loadavg_5}\", \
     \"{loadavg_15}\", \"{mem_total}\", \"{mem_avail}\", \"{disk_total}\", \"{disk_avail}\", \"{time0}\")".format(box_id=BOX_ID,
                                                                                                                 ip=IP,
                                                                                                                 port=PORT,
                                                                                                                 cpu_Hz=CPU_HZ,
                                                                                                                 cpu_num=CPU_NUM,
                                                                                                                 cpu_usr=CPU_USR,
                                                                                                                 cpu_sys=CPU_SYS,
                                                                                                                 cpu_nic=CPU_NIC,
                                                                                                                 cpu_idle=CPU_IDLE,
                                                                                                                 cpu_io=CPU_IO,
                                                                                                                 cpu_irq=CPU_IRQ,
                                                                                                                 cpu_sirq=CPU_SIRQ,
                                                                                                                 loadavg_1=LOADAVG_1,
                                                                                                                 loadavg_5=LOADAVG_5,
                                                                                                                 loadavg_15=LOADAVG_15,
                                                                                                                 mem_total=MEM_TOTAL,
                                                                                                                 mem_avail=MEM_AVAIL,
                                                                                                                 disk_total=DISK_TOTAL,
                                                                                                                 disk_avail=DISK_AVAIL,
                                                                                                                 time0=Time0)
    try:
        cursor.execute(sql)
        mdb.commit()
    except:
       print ("Error: unable to insert box-info data")

    mdb.close()

def mysql_update_box(BOX_ID,IP,PORT):
    mdb = pymysql.connect("localhost","root","elnj4j;3xj4","live_stream_db" )
    cursor = mdb.cursor()
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    selectsql="SELECT  `box-id` FROM `box` WHERE `box-id`=\"{box_id}\"".format(box_id=BOX_ID)
    insertsql="INSERT INTO `box`(`box-id`, `ip`, `port`, `time`) VALUES (\"{box_id}\",\"{ip}\",\"{port}\",\"{time0}\")".format(
    box_id=BOX_ID,ip=IP,port=PORT,time0=Time0)
    updatesql="UPDATE `box` SET `ip`=\"{ip}\",`port`=\"{port}\",`time`=\"{time0}\" WHERE `box-id`= \"{box_id}\" ".format(
    box_id=BOX_ID,ip=IP,port=PORT,time0=Time0)
    data=[]
    try:
        cursor.execute(selectsql)
        data=cursor.fetchall()
    except:
        print("Error: unable to search box box-id")
    if(len(data)==0):
        try:
            cursor.execute(insertsql)
            mdb.commit()
        except:
            print ("Error: unable to insert box data")
    else:
        try:
            cursor.execute(updatesql)
            mdb.commit()
        except:
            print ("Error: unable to update box data")
    mdb.close()
