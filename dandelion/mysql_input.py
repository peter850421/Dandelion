import pymysql
import datetime


def mysql_input(msg, conf, logger=None):
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = ""
    try:
        sql = "INSERT INTO `box_info`(`box-id`, `ip`, `port`, `cpu-Hz`, `cpu-num`, `cpu-usr`, \
         `cpu-sys`, `cpu-nic`, `cpu-idle`, `cpu-io`, `cpu-irq`, `cpu-sirq`, `loadavg-1`, `loadavg-5`, \
         `loadavg-15`, `mem-total`, `mem-avail`, `disk-total`, `disk-avail`,`time`) \
         VALUES (\"{box_id}\", \"{ip}\", \"{port}\", \"{cpu_Hz}\", \"{cpu_num}\", \"{cpu_usr}\", \
         \"{cpu_sys}\", \"{cpu_nic}\", \"{cpu_idle}\", \"{cpu_io}\", \"{cpu_irq}\", \"{cpu_sirq}\", \"{loadavg_1}\", \"{loadavg_5}\", \
         \"{loadavg_15}\", \"{mem_total}\", \"{mem_avail}\", \"{disk_total}\", \"{disk_avail}\", \"{time0}\")".format(
            box_id=msg['ID'],
            ip=msg['IP'],
            port=msg['PORT'],
            cpu_Hz=msg['CPU-HZ'],
            cpu_num=msg['CPU-NUM'],
            cpu_usr=msg['CPU-USR'],
            cpu_sys=msg['CPU-SYS'],
            cpu_nic=msg['CPU-NIC'],
            cpu_idle=msg['CPU-IDLE'],
            cpu_io=msg['CPU-IO'],
            cpu_irq=msg['CPU-IRQ'],
            cpu_sirq=msg['CPU-SIRQ'],
            loadavg_1=msg['LOADAVG-1'],
            loadavg_5=msg['LOADAVG-5'],
            loadavg_15=msg['LOADAVG-15'],
            mem_total=msg['MEM-TOTAL'],
            mem_avail=msg['MEM-AVAIL'],
            disk_total=msg['DISK-TOTAL'],
            disk_avail=msg['DISK-AVAIL'],
            time0=Time0)
    except KeyError:
        if logger:
            logger.exception("KeyError in msg while inserting box-info to mysql")
        return
    try:
        mdb = pymysql.connect(host=conf["mysql_host"],
                              user=conf["mysql_user"],
                              port=conf["mysql_port"],
                              database=conf["mysql_db"],
                              password=conf["mysql_password"])
        cursor = mdb.cursor()
        cursor.execute(sql)
        mdb.commit()
        mdb.close()
    except:
        if logger:
            logger.exception("Unable to connect to mysql or cannot insert box-info data")


def mysql_update_box(BOX_ID, IP, PORT, conf):
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    selectsql = "SELECT  `box-id` FROM `box` WHERE `box-id`=\"{box_id}\"".format(box_id=BOX_ID)
    insertsql = "INSERT INTO `box`(`box-id`, `ip`, `port`, `time`) VALUES (\"{box_id}\",\"{ip}\",\"{port}\",\"{time0}\")".format(
        box_id=BOX_ID, ip=IP, port=PORT, time0=Time0)
    updatesql = "UPDATE `box` SET `ip`=\"{ip}\",`port`=\"{port}\",`time`=\"{time0}\" WHERE `box-id`= \"{box_id}\" ".format(
        box_id=BOX_ID, ip=IP, port=PORT, time0=Time0)
    data = []
    try:
        mdb = pymysql.connect(host=conf["mysql_host"],
                              user=conf["mysql_user"],
                              port=conf["mysql_port"],
                              database=conf["mysql_db"],
                              password=conf["mysql_password"])
        cursor = mdb.cursor()
        cursor.execute(selectsql)
        data = cursor.fetchall()
    except:
        print("Error: unable to search box box-id")
        return
    if len(data) == 0:
        try:
            cursor.execute(insertsql)
            mdb.commit()
        except:
            print("Error: unable to insert box data")
    else:
        try:
            cursor.execute(updatesql)
            mdb.commit()
        except:
            print("Error: unable to update box data")
    mdb.close()

def mysql_traffic_flow(BOX_ID, URL, STATUS, SIZE, conf, logger=None):
    Time0 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sql = ""

    try:
        sql = "INSERT INTO `traffic_flow`(`BOX_ID`, `url`, `status`, `size`, `time`) \
                VALUES (\"{box_id}\",\"{url}\",\"{status}\",\"{size}\",\"{time0}\")".format(
            box_id=BOX_ID,
            url=URL,
            status=STATUS,
            size=SIZE,
            time0=Time0)
    except KeyError:
        if logger:
            logger.exception("KeyError in msg while inserting box-info to mysql")
        return

    try:
        mdb = pymysql.connect(host=conf["mysql_host"],
                              user=conf["mysql_user"],
                              port=conf["mysql_port"],
                              database=conf["mysql_db"],
                              password=conf["mysql_password"])
        self.logger.debug("Mysql debug %s " % sql)
        cursor = mdb.cursor()
        cursor.execute(sql)
        mdb.commit()
        mdb.close()
    except:
        if logger:
            logger.exception("Unable to connect to mysql or cannot insert box-info data")
