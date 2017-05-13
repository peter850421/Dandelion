# -*- coding: utf-8 -*-
from __future__ import print_function
from collections import OrderedDict
import pprint
import sys,os,time
import subprocess


def rule(words):
    for i in range (0,len(words)):
        words[i]=''.join(list(filter(lambda x:x in '0123456789.',words[i])))
    return(words)


def CPU_loading_info():
    cpu         = subprocess.check_output("top -b -n1|grep -E Cpu",shell=True).decode("utf-8").rsplit('\n', 1)[0].replace(' ','')
    cpu         = cpu.split(':',)[1].split(',',)
    cpu         = rule(cpu)
    return(cpu)


def Memory_info():
    mem         = subprocess.check_output("top -b -n1|grep -E Mem",shell=True).decode("utf-8").rsplit('\n', 1)[0].replace(' ','')
    mem         = mem.split('\n',)[0].split(',',)
    mem         = rule(mem)
    return(mem)


def Loadaverage_info():
    loading     = subprocess.check_output("top -b -n1|grep -E 'load average'",shell=True).decode('unicode-escape').rsplit('\n', 1)[0].split('\f', 1)[0].replace(' ','')
    loading     = loading[loading.find("load"):].split(',',)
    loading     = rule(loading)
    return(loading)


def Disk_info():
    info        = os.statvfs("/")
    total       = info.f_blocks*info.f_bsize/(1024*1024*1024)
    avail       = info.f_bfree*info.f_bsize/(1024*1024*1024)
    disk_info   = ['{0}'.format(total),'{0}'.format(avail)]
    return(disk_info)

def CPU_Hz():
    try:
        cpu_Hz    = subprocess.check_output("lscpu | grep 'max MHz'").decode("utf-8").rsplit('\n', 1)[0].replace(' ','').split(':',)
        cpu_Hz    = ''.join(list(filter(lambda x:x in '0123456789.',cpu_Hz[1])))
    except subprocess.CalledProcessError as e:
        cpu_Hz = 0
    return(cpu_Hz)


def CPU_number():
    cpu_number  = subprocess.check_output("grep 'processor' /proc/cpuinfo | wc -l",shell=True).decode("utf-8").rsplit('\n', 1)[0].replace(' ','')
    return(cpu_number)


s
if __name__=='__main__':
    print(CPU_number())
    print(CPU_loading_info())
    print(Memory_info())
    print(Loadaverage_info())
    print(Disk_info())
    print(CPU_Hz())
