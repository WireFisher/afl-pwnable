#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import shlex
import os
import multiprocessing
import threading
import Queue
import psutil
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from shellphuzz import start_fuzz

BINARY_DIR_PATH = "/home/binary/"

# 最长的fuzz时间，以分钟计
MAX_FUZZ_TIME = 120
# 单个fuzz任务使用的CPU个数
COMMON_AFL_CORES = 5
# 单个drilling任务使用的CPU个数
COMMON_DRILLING_CORES = 1

tasks = []
crash_inputs = multiprocessing.Queue()
processes = []

def start_new_fuzz_task(binary, afl_core, drilling_core):
    '''
        运行shellphuzz程序，启动线程接受接受结果，返回Process对象。
    '''
    q = multiprocessing.Queue()
    process = multiprocessing.Process(target=start_fuzz, args=(
        q, binary, afl_core, drilling_core
    ))

    def get_all_crash_inputs():
        while True:
            tmp = q.get()
            crash_inputs.put(tmp)
    
    t = threading.Thread(target=get_all_crash_inputs)
    t.daemon = True
    t.start()

    return process

def submit_input():
    '''
        开始提交输入的线程。
    '''
    def daemon(string_in):
        while True:
            tmp = crash_inputs.get()
            submit(tmp)             # TODO: 这里是你们要给我提供的接口函数
    t = threading.Thread(target=daemon, args=(string_in,))
    t.daemon = True
    t.start()

def get_finish_task():
    '''
        通过调用其它人的组件，得到已完成的任务列表，在服务重启时有用，待完成。
        任务通过二进制文件的绝对路径字符串来标识。
        TODO: 你们需要给我提供接口。
    '''
    return []

class FileCreateEventHandler(FileSystemEventHandler):
    def on_created(event):
        print("[ ] File %s created." % event.src_path)
        tasks.append(event.src_path)
    def on_modified(event):
        # TODO: 需先停止之前的任务，再添加新任务。
        pass

def watch_directory(path):
    '''
        事件驱动，监视二进制文件存放的文件夹，一旦文件发生变化就将二进制文件放置进入fuzz队列。
    '''
    # 添加文件夹中已有文件，并添加过滤程序
    files_already_exists = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files_already_exists = list(set(files_already_exists) - set(get_finish_task))
    tasks.extend(files_already_exists)

    # 监视文件夹
    event_handler = FileCreateEventHandler()
    observer = Observer()
    t = threading.Thread(target=observer.schedule, args=(event_handler, path))
    t.daemon = True
    t.start()
    print("[*] Directory watchdog started.")

def main():
    '''
        事件主循环。
    '''
    watch_directory(BINARY_DIR_PATH)
    task_scheduled = []
    while True:
        for task in tasks:
            if task not in task_scheduled:
                task_scheduled.append(task)
                start_new_fuzz_task(task, COMMON_AFL_CORES, COMMON_DRILLING_CORES)
        time.sleep(10)
    