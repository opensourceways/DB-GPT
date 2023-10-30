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

import jwt
import random
import string
import time

from pilot.configs.model_config import config_parser, raw_config_parser
from pilot.logs import logger
from pilot.utils.rsa_utils import encrypt_data, decrypt_data, generate_keys

class JwtTokenTool:
    base_jwt_secret = config_parser.get("app_authentication", "base_jwt_secret")
    jti_length = config_parser.get("app_authentication", "jti_length")
    rsa_public_key, rsa_private_key = generate_keys(int(config_parser.get("app_authentication", "rsa_key_length")))
    app_secret_map = config_parser.get("app_authentication", "app_secret_map")
    
    @classmethod
    def create_token(cls, app_id, app_secret, period) -> str:
        claims = {
            'iat': int(time.time()),
            'exp': int(time.time()) + int(period),
            'sub': app_id,
            'jti': _random_str(cls.jti_length)
        }
        try:
            token = jwt.encode(
                payload=claims,
                key=app_secret + cls.base_jwt_secret
            )
            return encrypt_data(token, cls.rsa_public_key)
        except Exception as e:
            logger.error("JWT generation fail", str(e))
    
    @classmethod
    def get_payload(cls, jwt_token, app_info):
        try:
            token = decrypt_data(jwt_token, cls.rsa_private_key)
            app_secret_dict = convert_str_to_dict(cls.app_secret_map)
            app_secret = app_secret_dict[app_info['app_id']]
            data = jwt.decode(token,  app_secret+ cls.base_jwt_secret, ['HS256'])
            return data
        except Exception as e:
            logger.error("JWT decryption fail", str(e))
            return "RSA key is expired."

def _random_str(length):
    return ''.join(random.sample(string.ascii_letters + string.digits, int(length)))

def convert_str_to_dict(data: str) -> dict:
    pairs = data.split(';')
    ret = {}
    for pair in pairs:
        key, value = pair.split(':')
        ret[key] = value
    return ret
