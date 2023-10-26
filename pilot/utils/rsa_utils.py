#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2023 The community Authors.
# A-Tune is licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
# PURPOSE.
# See the Mulan PSL v2 for more details.
# Create: 2023/10/17

import base64

from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

def generate_keys(length):
    random_generator = Random.new().read
    rsa = RSA.generate(length, random_generator)
    private_key = rsa.exportKey()
    public_key = rsa.publickey().exportKey()
    return public_key.decode('utf-8'), private_key.decode('utf-8')

def encrypt_data(msg, key):
    public_key = RSA.importKey(key)
    cipher = PKCS1_OAEP.new(public_key)
    encrypt_text = base64.urlsafe_b64encode(cipher.encrypt(bytes(msg.encode("utf8"))))
    return encrypt_text.decode('utf-8')

def decrypt_data(encrypt_msg, key):
    private_key = RSA.importKey(key)
    cipher = PKCS1_OAEP.new(private_key)
    back_text = cipher.decrypt(base64.urlsafe_b64decode(encrypt_msg))
    return back_text.decode('utf-8')
