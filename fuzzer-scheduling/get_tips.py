#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import os.path
import hashlib
import signal
import timeout_decorator

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

import testcase_gen


class TimeoutException(Exception):
    pass


class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutException(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


def tips_path(path):
    print("[*] Let's find out some tips.")

    @timeout_decorator.timeout(90, use_signals=False, timeout_exception=TimeoutException)
    def helper(path):
        tmp_path = os.path.join("/tmp", hashlib.sha256(path).hexdigest())
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        g = testcase_gen.tc_gen(path)
        g.run()
        with open(os.path.join(tmp_path, "testcase.txt"), "wb") as f:
            f.write(g.get_testcase())
        print("[ ] testcase-gen success.")
        return tmp_path

    try:
        tmp_path = helper(path)
    except TimeoutException:
        print("[!] testcase-gen timeout!")
        return None
    except RuntimeError:
        print("[!] testcase-gen error!")
        return None

    return tmp_path
