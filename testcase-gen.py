#!/usr/bin/env python2

import re
from zio import *

_TIMEOUT = 3
separators = ['. ', ': ', '.', ':', ' ']

class tc_gen():

    def __init__(self, executable):
        """
        example:

        g = tc_gen("./welpwn")
        """

        if not isinstance(executable, str):
            raise Exception("please set a string of filename :)")
        
        self.executable = executable
        self.load_executable()

        self.sentences = []
        self.firstwords = {}
        self.potential_seps = []

    def recvline(self):
        return self.io.read_until(["\r\n", "\n", EOF], timeout=_TIMEOUT)

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
        
        for sentence in self.sentences:
            result = self.get_first(sentence)
            if result:
                for sep in result:
                    if sep in self.firstwords:
                        self.firstwords[sep] += result[sep]
                    else:
                        self.firstwords[sep] = result[sep]
        print self.firstwords

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

        print self.potential_seps

    def send_for_test(self, s):
        try:
            self.io.close()
            self.load_executable()
            self.recvuntil(self.sentences[-1], timeout=_TIMEOUT)
        except TIMEOUT:
            return '' #don't know what to do

        self.sendline(s)
        
        try:
            return self.recvline()
        except TIMEOUT:
            return ''

    def test_potential(self):
        for sep in self.potential_seps:
            is_different = False
            response = self.send_for_test(self.firstwords[sep][0])
            for word in self.firstwords[sep][1:]:
                self.send_for_test(word)
#TODO pick out words that are valid, use abnormal to test


if __name__ == "__main__":
    g = tc_gen("./bin/simple_note")
    #print g.recvline()
    g.analyze()
    print g.send_for_test('1')
