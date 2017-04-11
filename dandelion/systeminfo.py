# -*- coding: utf-8 -*-
from __future__ import print_function
from collections import OrderedDict
import pprint
import sys,os,time
import subprocess

def CPU_loading_info():
    cpu         = subprocess.check_output("top -b -n1|grep -E Cpu",shell=True).decode("utf-8").rsplit('\n', 1)[0]
    return(cpu)
def Memory_info():
    mem         = subprocess.check_output("top -b -n1|grep -E Mem",shell=True).decode("utf-8").rsplit('\n', 1)[0]
    return(mem)
def Loadaverage_info():
    loading     = subprocess.check_output("top -b -n1|grep -E 'load average'",shell=True).decode('unicode-escape').rsplit('\n', 1)[0].split('\f', 1)[0]
    a           = loading.find("load")
    return(loading[a:])
def Disk_info():
    info        = os.statvfs("/")
    total       = info.f_blocks*info.f_bsize/(1024*1024*1024)
    avail       = info.f_bfree*info.f_bsize/(1024*1024*1024)
    disk_info   ={"total":total,"avail":avail}
    return(disk_info)
def CPU_number():
    ''' Return the information in /proc/CPUinfo
    as a dictionary in the following format:
    CPU_info['proc0']={...}
    CPU_info['proc1']={...}
    '''
    CPUinfo=OrderedDict()
    procinfo=OrderedDict()

    nprocs = 0
    with open('/proc/cpuinfo') as f:
        for line in f:
            if not line.strip():
                # end of one processor
                CPUinfo['proc%s' % nprocs] = procinfo
                nprocs=nprocs+1
                # Reset
                procinfo=OrderedDict()
            else:
                if len(line.split(':')) == 2:
                    procinfo[line.split(':')[0].strip()] = line.split(':')[1].strip()
                else:
                    procinfo[line.split(':')[0].strip()] = ''

    cpu_info=[]
    for processor in CPUinfo.keys():
        cpu_info.append(CPUinfo[processor]['model name'])
    return(cpu_info)



if __name__=='__main__':
    print(CPU_number())
    print(CPU_loading_info())
    print(Memory_info())
    print(Loadaverage_info())
    print(Disk_info())
