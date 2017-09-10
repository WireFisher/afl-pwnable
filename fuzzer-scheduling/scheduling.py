#!/usr/bin/env python2
# -*- coding: utf-8 -*- 

import os
import multiprocessing
import threading
import time
import process_util
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
# 最多允许同时运行的task个数
MAX_TASKS_RUNNING = 3

tasks = []
crash_inputs = multiprocessing.Queue()
processes = []


################# DUMMY FUNCTION #################

def submit(i):
    print("[!] Pretend to submit...: %s" % i)


def get_finish_task():
    """
        通过调用其它人的组件，得到已完成的任务列表，在服务重启时有用，待完成。
        任务通过二进制文件的绝对路径字符串来标识。
        TODO: 你们需要给我提供接口。
    """
    return []

##################################################


class ProcessManager(object):
    def __init__(self):
        self.task_scheduled = []
        self.task_paused = []
        self.task_finished = []
        print("[*] Process Manager started!")

    def watch_processes(self):
        def helper():
            while True:
                time.sleep(10)
                for p in processes:
                    # 完成了则清除进程
                    if not p.is_alive():
                        self.task_finished.append(p)
                        self.task_scheduled.remove(p)
                        print("[*] Task %s is finished!" % p.name)

                    # 检查进程是否超时，超时则暂停进程
                    if time.time() > p.end_time:
                        process_util.pause_process(p.pid)
                        self.task_scheduled.remove(p)
                        self.task_paused.append(p)
                        print("[ ] Task %s is paused." % p.name)

        t1 = threading.Thread(target=helper)
        t1.daemon = True
        t1.start()

        def resume_helper():
            while True:
                time.sleep(60 * 5)
                if len(self.task_scheduled) < MAX_TASKS_RUNNING and len(self.task_paused):
                    for p in self.task_paused:
                        if len(self.task_scheduled) < MAX_TASKS_RUNNING:
                            p.end_time = time.time() + 30 * 60
                            self.task_scheduled.append(p)
                            self.task_paused.remove(p)
                            process_util.resume_process(p.pid)
                            print("[ ] Task %s is resumed." % p.name)
        t2 = threading.Thread(target=resume_helper)
        t2.daemon = True
        t2.start()

    def add_new_task(self, binary):
        if len(self.task_scheduled) > MAX_TASKS_RUNNING:
            pass
        else:
            self.task_scheduled.append(binary)
            p = start_new_fuzz_task(binary, COMMON_AFL_CORES, COMMON_DRILLING_CORES)
            # 给process对象添加一些属性，以便于管理。
            p.start_time = time.time()
            p.end_time = p.start_time + MAX_FUZZ_TIME * 60
            p.path = binary
            processes.append(p)
            print("[*] Task %s is added." % p.name)

    def check_binary_directory(self):
        def helper():
            while True:
                for task in tasks:
                    names = [n.path for n in self.task_scheduled] + \
                            [n.path for n in self.task_finished] + \
                            [n.path for n in self.task_paused]
                    if task not in names:
                        self.add_new_task(task)
                time.sleep(10)

        t = threading.Thread(target=helper)
        t.daemon = True
        t.start()

    def duty(self):
        self.check_binary_directory()
        self.watch_processes()


def start_new_fuzz_task(binary, afl_core, drilling_core):
    """
        运行shellphuzz程序，返回Process对象。
    """
    process = multiprocessing.Process(target=start_fuzz, args=(
        crash_inputs, binary, afl_core, drilling_core
    ))

    return process


def submit_input():
    """
        开始提交输入的线程。
    """

    def helper():
        while True:
            tmp = crash_inputs.get()
            submit(tmp)  # TODO: 这里是你们要给我提供的接口函数

    t = threading.Thread(target=helper)
    t.daemon = True
    t.start()


class FileCreateEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        print("[ ] File %s created." % event.src_path)
        tasks.append(event.src_path)

    def on_modified(self, event):
        # TODO: 需先停止之前的任务，再添加新任务。
        pass


def watch_directory(path):
    """
        事件驱动，监视二进制文件存放的文件夹，一旦文件发生变化就将二进制文件放置进入fuzz队列。
    """
    # 添加文件夹中已有文件，并添加过滤程序
    files_already_exists = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files_already_exists = list(set(files_already_exists) - set(get_finish_task()))
    tasks.extend(files_already_exists)

    # 监视文件夹
    event_handler = FileCreateEventHandler()
    observer = Observer()
    t = threading.Thread(target=observer.schedule, args=(event_handler, path))
    t.daemon = True
    t.start()
    print("[*] Directory watchdog started.")


def main():
    """
        事件主循环。
    """
    watch_directory(BINARY_DIR_PATH)
    ProcessManager().duty()
    submit_input()


if __name__ == '__main__':
    main()
