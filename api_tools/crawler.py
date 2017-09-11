#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import hashlib
import shutil

HTTP_HEADER = {
    'Content-Type': 'application/json',
    'Accept-Charset': 'utf-8',
    'Accept': 'text/plain'
}


def download_challenge(challenge, directory):
    name = challenge['name']
    meta_file = os.path.join(directory, name, 'metadata.json')
    binary_url = challenge['binary_url']
    binary_file = os.path.join(directory, name, name)

    print('======================')
    print('Processing challenge', name)

    if not os.path.exists(os.path.join(directory, name)):
        print('Creating directory for', name)
        os.makedirs(os.path.join(directory, name))

    if not os.path.exists(meta_file):
        print('Writing metadata for', name)
        with open(meta_file, 'w') as metadata:
            json.dump(challenge, metadata)

    else:
        with open(meta_file, 'r+') as metadata:
            rewrite = False
            try:
                old_metadata = json.load(metadata)
                if old_metadata != challenge:
                    rewrite = True
                else:
                    print('Metadata unchanged')
            except json.decoder.JSONDecodeError:
                rewrite = True
            if rewrite:
                print('Writing new metadata')
                metadata.seek(0)
                json.dump(challenge, metadata)

    print('Downloading binary')
    binary = requests.get(binary_url).content
    download_md5 = hashlib.md5(binary).hexdigest()
    print('Downloaded file MD5:', download_md5)

    if not os.path.exists(binary_file):
        print('Binary not existed, writing to file')
        with open(binary_file, 'wb') as file:
            file.write(binary)
    else:
        print('Binary existed, checking MD5')
        with open(binary_file, 'rb+') as file:
            old_md5 = hashlib.md5(file.read()).hexdigest()
            print('Existed file MD5:', old_md5)
            if download_md5 == old_md5:
                print('Good, MD5 unchanged.')
            else:
                print('Oh no, MD5 changed, writing new file')
                file.seek(0)
                file.write(binary)
    os.chmod(binary_file, 0o755)

    hm_payload_path = '/root/Code/afl-pwnable/handmade_payload'
    for file_name in os.listdir(hm_payload_path):
        full_file_name = os.path.join(hm_payload_path, file_name)
        full_file_name_dst = os.path.join(directory, file_name)
        if (os.path.isfile(full_file_name)):
            try:
                shutil.copy(full_file_name, full_file_name_dst)
            except IOException:
                continue


def crawl_challenges(url, token, directory):
    r = requests.post(url, headers=HTTP_HEADER, json={
        'token': token
    })
    if r.status_code == 200:
        result = r.json()
        if result['status'] == 'ok':
            for challenge in result['challenges']:
                # print(challenge)
                download_challenge(challenge, directory)


if __name__ == '__main__':
    with open(os.path.join(os.path.dirname(__file__), 'config.json')) as configFile:
        config = json.load(configFile)
        crawl_challenges(config['challenges_url'], config['token'], config['directory'])
