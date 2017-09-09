#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import subprocess
import shlex
import os
import multiprocessing
import shellphuzz

BINARY_DIR_PATH = "/home/binary/"

# 最长的fuzz时间，以分钟计
MAX_FUZZ_TIME = 120
# 单个fuzz任务使用的CPU个数
COMMON_AFL_CORES = 5
# 单个drilling任务使用的CPU个数
COMMON_DRILLING_CORES = 1

tasks = []

def start_new_fuzz_task(binary, afl_core, drilling_core):
    '''
        运行shellphuzz程序，返回Popen对象。
    '''
    pass

