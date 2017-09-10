#!/usr/bin/env python2

import re
import time
from zio import *

_TIMEOUT = 0.2
separators = ['. ', ': ', '.', ':', ' ']

inputs  = ['!z9@']      # wrong input
inputs += ['0']         # index
inputs += ['1']
inputs += ['4']         # size
inputs += ['16']
inputs += ['130']
inputs += ['a' * 4]     # string
inputs += ['a' * 16]
inputs += ['a' * 130]


class tc_gen():

    def __init__(self, executable):
        """
        example:

        g = tc_gen("./welpwn")
        """

        if not isinstance(executable, str):
            raise Exception("please set a string of filename :)")
        
#TODO chmod 777
        self.executable = executable
        self.load_executable()

        self.have_menu = False
        self.sentences = []
        self.firstwords = {}
        self.potential_seps = []
        self.sep = ''
        self.menu_lastline = ''
        self.testcase = []
        self.exploit = ''

        self.analyze()

    def recvline(self):
        return self.io.read_until(["\r\n", "\n", EOF], timeout=_TIMEOUT)

    def recvall(self):
        ret = []
        while True:
            try:
                r = self.io.read_until(["\r\n", "\n", EOF], timeout=_TIMEOUT)
                if len(r) > 0:
                    ret += [r]
                else:     # When process exited anyway, r = ""
                    break
            except TIMEOUT:
                break

        return ret
    
    def load_executable(self):
        self.io = zio(self.executable, print_read=False, print_write=False)
        self.recv = self.io.read
        #self.recvline = self.io.readline
        self.recvuntil = self.io.read_until
        self.send = self.io.write
        self.sendline = self.io.writeline
        
    def get_first(self, string):
        found = False
        for separator in separators:
            substrs = string.split(separator)
            if substrs[0] != string:
                found = True
                break
        if not found:
            return []
        return {separator: [substrs[0]]}

    def analyze(self):
        '''Analyze the output of the binary, strip each line, save the first words and choose potential separators

           Rules:
               1. Words are in the same format, eg. [1-9], [a-Z].
               2. Words' length has to be same
               3. The amount of words has to be lager than 1'''

        while True:
            try:
                self.sentences += [self.recvline()]
            except TIMEOUT:
                break
        
        if len(self.sentences) > 0:
            self.menu_lastline = self.sentences[-1]

        for sentence in self.sentences:
            result = self.get_first(sentence)
            if result:
                for sep in result:
                    if sep in self.firstwords:
                        self.firstwords[sep] += result[sep]
                    else:
                        self.firstwords[sep] = result[sep]
        #print self.firstwords

        '''count and pick out potential words to be choice-characters'''
        for sep in self.firstwords:
            if len(self.firstwords[sep]) > 1:
                length = len(self.firstwords[sep][0])
                isdigit = self.firstwords[sep][0].isdigit()
                isalpha = self.firstwords[sep][0].isalpha()
                for word in self.firstwords[sep]:
                    if length != len(word) or isdigit != word.isdigit() or isalpha != word.isalpha():
                        continue
                self.potential_seps += [sep]
        
        #print "potential_seps"
        #print self.potential_seps

    def send_for_test(self, s):
        try:
            self.io.close()
            self.load_executable()
            self.recvuntil(self.menu_lastline, timeout=_TIMEOUT)
        except TIMEOUT:
            return [] # don't know what to do

        self.sendline(s)
        
        try:
            return [self.recvline()]
        except TIMEOUT:
            return []

    def restart_sendline(self, s):
        try:
            self.io.close()
            self.load_executable()
            self.recvuntil(self.menu_lastline, timeout=_TIMEOUT)
        except TIMEOUT:
            return  # This shouldn't happened

        if isinstance(s, str):
            self.sendline(s)

        if isinstance(s, list):
            try:
                for string in s:
                    self.sendline(string)
                    time.sleep(0.01)
            except:
                return # This shouldn't happened
            

    def test_potential(self):
        for sep in self.potential_seps:
            is_different = False
            response = []
            if len(self.firstwords[sep]) == 0:
                continue
            response += self.send_for_test(self.firstwords[sep][0])
            for word in self.firstwords[sep][1:]:
                response += self.send_for_test(word)

            for i in range(0, len(response)):
                for j in range(i, len(response)):
                    if response[i] == response[j]:
                        is_different = True
                        break
                if is_different:
                    break
            if is_different:
                self.sep = sep
                break

    def test_suboption(self):
        if self.sep == "":
            return

        options = self.firstwords[self.sep]
        for option in options:
            self.restart_sendline(option)
            try:
                response = self.recvline()
            except OSError:
                continue

            self.testcase += [option]
            if response == self.menu_lastline:
                continue
            
            ''' test each string in inputs, save the responses'''
            lastline = ""
            loop_count = 0
            while lastline != self.menu_lastline and loop_count < 8: # loop_count < 8 to avoid infinite loop
                all_empty = True
                responses = []
                print self.testcase
                print "lastline: " + lastline
                for pattern in inputs:
                    print pattern
                    try:
                        self.restart_sendline(self.testcase)      # have problems when it's read() and doesn't stop at \n
                        #self.recvuntil(lastline, timeout=_TIMEOUT)
                        self.recvall()
                        self.sendline(pattern)
                        ret = self.recvall()
                        print ret
                        if len(ret) > 0:
                            responses += [ret[-1]]
                        else:
                            responses += [""]

                    except OSError:
                        responses += [""]

                for i in range(0, len(responses)):
                    print responses[i]
                    if len(responses[i]) > 0:
                        all_empty = False
                    if i == 0:
                        continue
                    if responses[i] != responses[0] or responses[i] == self.menu_lastline:
                        self.testcase += [inputs[i]]
                        lastline = responses[i]
                        break

                if all_empty:
                    break
                loop_count += 1

#TODO: - pick out words that are valid, use abnormal to test
#      - set Timeout value properly


if __name__ == "__main__":
    g = tc_gen("./bin/simple_note")
    g.test_potential()
    g.test_suboption()
    print g.testcase
