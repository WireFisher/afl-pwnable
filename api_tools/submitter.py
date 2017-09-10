#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import time
import nclib
import glob


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


def submit_challenge(token, d):
    print('======================')
    print('Found challenge', d)
    payload_files = glob.glob(os.path.join(d, 'payload.bin.*'))

    for payload_file in payload_files:
        if 'success' in payload_file:  # success flag
            continue

        print('Payload found:' + payload_file)
        if os.path.exists(payload_file + '.success'):
            print('Already successfully solved, skipping to next')
            continue
        else:
            with open(d + '/metadata.json') as meta_file:
                payload = open(payload_file, 'rb').read()
                metadata = json.load(meta_file)
                access = metadata['access']
                for server in access:
                    if submit_to_server(server, payload, token):
                        with open(payload_file + '.success', 'w') as flag:
                            flag.write(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                        print('Successfully solved!')
                        return True
                print('All attempts failed')
    else:
        print('Payload not found, skipping to next')


if __name__ == '__main__':
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as configFile:
        config = json.load(configFile)
        for roots, dirs, files in os.walk(config['directory']):
            for d in dirs:
                working_dir = os.path.join(config['directory'], d)
                if os.path.exists(working_dir) and os.path.exists(os.path.join(working_dir, '/metadata.json')):
                    submit_challenge(config['token'], working_dir)
