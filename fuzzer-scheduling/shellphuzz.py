#!/usr/bin/env python

import os
import sys
import imp
import time
import fuzzer
import shutil
import socket
import driller
import tarfile
import importlib
import logging.config

def start_fuzz(queue, binary, afl_cores=1, driller_workers=None, grease_with=None, force_interval=None, 
               work_dir="/dev/shm/work/", first_crash=False, timeout=None, ipython=False, tarball=None, 
               helper_module=None, no_dictionary=False, logcfg=".shellphuzz.ini"):
    """
        parser.add_argument('binary', help="the path to the target binary to fuzz")
        parser.add_argument('-g', '--grease-with', help="A directory of inputs to grease the fuzzer with when it gets stuck.")
        parser.add_argument('-d', '--driller_workers', help="When the fuzzer gets stuck, drill with N workers.", type=int)
        parser.add_argument('-f', '--force_interval', help="Force greaser/fuzzer assistance at a regular interval (in seconds).", type=float)
        parser.add_argument('-w', '--work-dir', help="The work directory for AFL.", default="/dev/shm/work/")
        parser.add_argument('-c', '--afl-cores', help="Number of AFL workers to spin up.", default=1, type=int)
        parser.add_argument('-C', '--first-crash', help="Stop on the first crash.", action='store_true', default=False)
        parser.add_argument('-t', '--timeout', help="Timeout (in seconds).", type=float)
        parser.add_argument('-i', '--ipython', help="Drop into ipython after starting the fuzzer.", action='store_true')
        parser.add_argument('-T', '--tarball', help="Tarball the resulting AFL workdir for further analysis to this file -- '{}' is replaced with the hostname.")
        parser.add_argument('-m', '--helper-module', help="A module that includes some helper scripts for seed selection and such.")
        parser.add_argument('--no-dictionary', help="Do not create a dictionary before fuzzing.", action='store_true', default=False)
        parser.add_argument('--logcfg', help="The logging configuration file.", default=".shellphuzz.ini")
        args = parser.parse_args()
    """
    crash_input_set = set()

    if os.path.isfile(os.path.join(os.getcwd(), logcfg)):
        logging.config.fileConfig(os.path.join(os.getcwd(), logcfg))

    try: os.mkdir("/dev/shm/work/")
    except OSError: pass

    if helper_module:
        try:
            helper_module = importlib.import_module(helper_module)
        except (ImportError, TypeError):
            helper_module = imp.load_source('fuzzing_helper', helper_module)
    else:
        helper_module = None

    drill_extension = None
    grease_extension = None

    if grease_with:
        print "[*] Greasing..."
        grease_extension = fuzzer.GreaseCallback(
            grease_with,
            grease_filter=helper_module.grease_filter if helper_module is not None else None,
            grease_sorter=helper_module.grease_sorter if helper_module is not None else None
        )
    if driller_workers:
        print "[*] Drilling..."
        drill_extension = driller.LocalCallback(num_workers=driller_workers)

    stuck_callback = (
        (lambda f: (grease_extension(f), drill_extension(f))) if drill_extension and grease_extension
        else drill_extension or grease_extension
    )

    print "[*] Creating fuzzer..."
    fuzzer = fuzzer.Fuzzer(
        binary, work_dir, afl_count=afl_cores, force_interval=force_interval,
        create_dictionary=not no_dictionary, stuck_callback=stuck_callback, time_limit=timeout
    )

    # start it!
    print "[*] Starting fuzzer..."
    fuzzer.start()
    start_time = time.time()

    try:
        # if timeout or first_crash:
        if True: 
            # 周期性的检查是否出现了新的可导致崩溃的测试用例

            while True:
                time.sleep(10)
                if fuzzer.found_crash():
                    crash_input_set_new = set(fuzzer.crashes())
                    if crash_input_set_new != crash_input_set:
                        # 向上提交
                        diffs = crash_input_set_new - crash_input_set
                        for sample in diffs:
                            print "[*] New crash sample: %s" % sample
                            queue.put((binary, sample))
                            crash_input_set.add(sample)
                if fuzzer.timed_out():
                    print "[*] Fuzzer Timeout reached."
                    break
    except KeyboardInterrupt:
        print "[*] Aborting wait. Ctrl-C again for KeyboardInterrupt."
    except Exception as e:
        print "[*] Unknown exception received (%s). Terminating fuzzer." % e
        fuzzer.kill()
        if drill_extension:
            drill_extension.kill()
        raise

    if ipython:
        print "[!]"
        print "[!] Launching ipython shell. Relevant variables:"
        print "[!]"
        print "[!] fuzzer"
        print "[!] driller_extension"
        print "[!] grease_extension"
        print "[!]"
        import IPython; IPython.embed()

    print "[*] Terminating fuzzer."
    fuzzer.kill()
    if drill_extension:
        drill_extension.kill()

    if tarball:
        print "[*] Dumping results..."
        p = os.path.join("/tmp/", "afl_sync")
        try:
            shutil.rmtree(p)
        except (OSError, IOError):
            pass
        shutil.copytree(fuzzer.out_dir, p)

        tar_name = tarball.replace("{}", socket.gethostname())

        tar = tarfile.open("/tmp/afl_sync.tar.gz", "w:gz")
        tar.add(p, arcname=socket.gethostname()+'-'+os.path.basename(binary))
        tar.close()
        print "[*] Copying out result tarball to %s" % tar_name
        shutil.move("/tmp/afl_sync.tar.gz", tar_name)
