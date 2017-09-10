#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import psutil

def pause_process(pid):
    p = psutil.Process(pid)
    p.suspend()

def resume_process(pid):
    p = psutil.Process(pid)
    p.resume()