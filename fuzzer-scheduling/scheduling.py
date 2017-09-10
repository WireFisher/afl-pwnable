#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import multiprocessing
import threading
import time
import process_util
import get_tips
import random
import string
import pdb
from shellphuzz import start_fuzz
from pyfiglet import Figlet

WORKING_DIR_PATH = "/tmp/work"

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
# processes = []


def submit(binary, i):
    print("[!] Submit...: \n[ ]Path: %s %s" % (binary, i))
    problem_dir = os.path.dirname(binary)
    random_suffix = "".join([
        random.choice(string.ascii_letters + string.digits) for _ in range(8)
    ])
    payload_filename = os.path.join(problem_dir, "payload.bin." + random_suffix)
    with open(payload_filename, "wb") as f:
        f.write(i)


def get_finish_task():
    """
        通过调用其它人的组件，得到已完成的任务列表，在服务重启时有用，
        任务通过二进制文件的绝对路径字符串来标识。
    """
    problems_dir = [
        f for f in os.listdir(WORKING_DIR_PATH)
        if os.path.isdir(os.path.join(WORKING_DIR_PATH, f))
    ]
    ans = []
    for problem in problems_dir:
        # print("*********************************")
        # print(os.listdir(os.path.join(WORKING_DIR_PATH, problem)), any([f.endswith("success") for f in os.listdir(os.path.join(WORKING_DIR_PATH, problem))]))
        # print("*********************************")
        if any([
           f.endswith("success") for f in os.listdir(os.path.join(WORKING_DIR_PATH, problem))
        ]):
            ans.append(os.path.join(WORKING_DIR_PATH, problem, problem))
    return ans


class ProcessManager(object):
    def __init__(self):
        self.task_scheduled = []
        self.task_paused = []
        self.task_finished = []
        print("[*] Process Manager started!")

    def watch_processes(self):
        print("[*] Starting watching processes states!")

        def helper():
            while True:
                time.sleep(10)
                for p in self.task_scheduled:
                    # 完成了则清除进程
                    if p.path in get_finish_task():
                        p.terminate()
                        self.task_finished.append(p)
                        self.task_scheduled.remove(p)
                        print("[*] Task %s is stopped!" % p.name)

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
            # print("[ ] Binary %s start analysis." % binary)
            p = start_new_fuzz_task(binary, COMMON_AFL_CORES, COMMON_DRILLING_CORES, get_tips.tips_path(binary))
            # p = start_new_fuzz_task(binary, COMMON_AFL_CORES, COMMON_DRILLING_CORES, None)
            # 给process对象添加一些属性，以便于管理。
            p.start_time = time.time()
            p.end_time = p.start_time + MAX_FUZZ_TIME * 60
            p.path = binary
            self.task_scheduled.append(p)
            print("[*] Task %s is added." % p.path)

    def check_binary_directory(self):
        print("[*] Starting watching working directory!")

        def helper():
            while True:
                problems_dir = [
                    os.path.join(WORKING_DIR_PATH, f) for f in os.listdir(WORKING_DIR_PATH)
                    if os.path.isdir(os.path.join(WORKING_DIR_PATH, f))
                ]
                problems_names = [os.path.basename(n.path) for n in self.task_scheduled]
                finished_names = [os.path.basename(n.path) for n in self.task_finished]
                paused_names = [os.path.basename(n.path) for n in self.task_paused]
                print("[*] Loaded problems: %s" % problems_names)
                print("[*] Finished problems: %s" % finished_names)
                print("[*] Paused problems: %s" % paused_names)
                bin_files = [os.path.join(f, os.path.basename(f)) for f in problems_dir
                             if os.path.exists(os.path.join(f, os.path.basename(f)))]
                for task in bin_files:
                    names = [x.path for x in self.task_scheduled] + \
                            [x.path for x in self.task_finished] + \
                            [x.path for x in self.task_paused]
                    if task not in names:
                        self.add_new_task(task)
                time.sleep(10)

        t = threading.Thread(target=helper)
        t.daemon = True
        t.start()

    def duty(self):
        self.check_binary_directory()
        self.watch_processes()


def start_new_fuzz_task(binary, afl_core, drilling_core, grease_with=None):
    """
        运行shellphuzz程序，返回Process对象。
    """
    print("==============================================")
    process = multiprocessing.Process(target=start_fuzz, args=(
        crash_inputs, binary, afl_core, drilling_core, grease_with
    ))
    process.start()

    return process


def submit_input():
    """
        开始提交输入的线程。
    """

    def helper():
        while True:
            tmp = crash_inputs.get()
            submit(*tmp)

    t = threading.Thread(target=helper)
    t.daemon = True
    t.start()
    return t


def main():
    """
        事件主循环。
    """
    f = Figlet(font='standard')
    print(f.renderText('Weicome to AFL-pwnable'))
    ProcessManager().duty()
    t = submit_input()


if __name__ == '__main__':
    main()
    while True:
        time.sleep(1)
