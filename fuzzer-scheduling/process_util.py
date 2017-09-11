#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import psutil

def pause_process(pid):
    p = psutil.Process(pid)
    p.suspend()

def resume_process(pid):
    p = psutil.Process(pid)
    p.resume()

def kill_process_familly(pid):
    parent = psutil.Process(pid)
    children = []
    for child in parent.children(recursive=True):  # or parent.children() for recursive=False
        children.append(child)
    for x in children:
        x.kill()
