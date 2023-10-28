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
# Create: 2023/10/13

import json
import logging
import requests
import redis

from pilot.configs.model_config import config_parser

logger = logging.getLogger("model_worker")


class Moderation:
    def __init__(self) -> None:
        self.configs = config_parser
        self.token_url = self.configs.get('moderation', 'token_url')
        self.moderation_url = self.configs.get('moderation', 'moderation_url')
        self.project_id = self.configs.get('moderation', 'project_id')
        self.username = self.configs.get('moderation', 'username')
        self.password = self.configs.get('moderation', 'password')
        self.domain = self.configs.get('moderation', 'domain')
        self.redis_host = self.configs.get('redis', 'redis_host')
        self.redis_port = self.configs.getint('redis', 'redis_port')
        self.redis_db = self.configs.getint('redis', 'redis_db')
        self.redis_password = self.configs.get('redis', 'redis_password')
        self.redis = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db, password=self.redis_password)

    def get_token(self, username, password, domain, project):
        token = self.redis.get('moderation_token')
        if token:
            return token

        headers = {
            "Content-Type": "application/json;charset=utf-8",
        }
        
        token_data = {
            "auth": {
                "identity": {
                    "methods": [
                        "password"
                    ],
                    "password": {
                        "user": {
                            "name": username,
                            "password": password,
                            "domain": {
                                "name": domain
                            }
                        }
                    }
                },
                "scope": {
                    "project": {
                        "id": project,
                        "name": "cn-north-4"
                    }
                }
            }
        }     
        response = requests.post(url=self.token_url, data=json.dumps(token_data), headers=headers)
        token = response.headers.get("X-Subject-Token")
        self.redis.set('moderation_token', token, 36000)
        logger.info('...refresh token succeed...')
        return token

    def check_text(self, text):
        token = self.get_token(self.username, self.password, self.domain, self.project_id)
        body = {
            "categories": ["terrorism"],
            "items": [{
                "text": text,
                "type": "content"
            }
            ]
        }
        _header = {
            "Content-Type": 'application/json',
            'X-Auth-Token': token
        }
        response = requests.post(url=self.moderation_url, data=json.dumps(body).encode('utf-8'), headers=_header)
        try:
            if response.json().get('result').get('suggestion') == 'pass':
                return True
        except:
            return False
        return False

