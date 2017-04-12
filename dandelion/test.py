from systeminfo import CPU_loading_info, Memory_info, Loadaverage_info, Disk_info, CPU_number
from mysql_input import mysql_input
if __name__ == '__main__':
    msg={'ID': 'box-142f108a279146ab90438e228e9fbf59', 'IP': '140.115.213.55', 'PORT': 8000, 'TYPE': 'BOX', 'COMMAND': 'EXCHANGE', 'CONNECT_WS': 'http://140.115.213.55:8000/dandelion/box-142f108a279146ab90438e228e9fbf59/ws', 'CPU_NUM': 'CPUmaxMHz:1536.0000\nCPUminMHz:480.0000', 'CPU_LOADING': '%Cpu(s):6.6us,2.8sy,0.0ni,89.7id,0.6wa,0.0hi,0.2si,0.0st', 'LOADING_AVG': 'loadaverage:3.45,3.27,3.20', 'Memory': 'KiBMem:2066484total,470188used,1596296free,12716buffers\nKiBSwap:0total,0used,0free.178936cachedMem', 'DISK': "{'total': 29.026622772216797, 'avail': 25.610458374023438}"}

    mysql_input(msg['IP'],msg['PORT'],msg['ID'],msg['CPU_NUM'],msg['CPU_LOADING'],msg['LOADING_AVG'],msg['Memory'],msg['DISK'])
