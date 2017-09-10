#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import nclib


def submit_to_server(server, payload, token):
    try:
        print('Connecting to', server)
        nc = nclib.Netcat((server['ip'], server['port']), verbose=False)
        nc.settimeout(5)
        result = nc.recv_until('Token:'.encode())
        print('Server message:', result)
        print('Received token request, sending token to server...', token)
        nc.send((token + '\n').encode())
        print('Sending payload to server...', payload)
        nc.send(payload)
        result = nc.recv_until('detected'.encode())
        print('Server message:', result)
        print('"detected" found. Success!')
        return True

    except nclib.NetcatError:
        print('Network error. Failed!')
        return False

    except ValueError:
        print('"detected" not found. Failure!')
        return False


def submit_challenge(token, location):
    print('======================')
    print('Found challenge', d)
    if os.path.exists(d + '/payload.bin'):
        print('Payload found')
        if os.path.exists(d + '/success.flag'):
            print('Already successfully solved, skipping to next')
            return
        else:
            with open(d + '/metadata.json') as meta_file:
                payload = open(d + '/payload.bin', 'rb').read()
                metadata = json.load(meta_file)
                access = metadata['access']
                for server in access:
                    if submit_to_server(server, payload, token):
                        with open(d + '/success.flag', 'w') as flag:
                            flag.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                        print('Successfully solved!')
                        return
                print('All attempts failed')
    else:
        print('Payload not found, skipping to next')


if __name__ == '__main__':
    with open('config.json') as configFile:
        config = json.load(configFile)
        for roots, dirs, files in os.walk(config['directory']):
            for d in dirs:
                if os.path.exists(d) and os.path.exists(d + '/metadata.json'):
                    submit_challenge(config['token'], d)
