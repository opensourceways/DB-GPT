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

import hashlib
import time
from fastapi import Request

from pilot.logs import logger
from pilot.authenticaton.base_authenticator import BaseAuthenticator
from pilot.authenticaton.jwt_token_tool import JwtTokenTool, convert_str_to_dict
from pilot.connections.redis import RedisConnector

class AppAuthenticator(BaseAuthenticator):
    def __init__(self) -> None:
        super().__init__()
        self.token_validity_period = self.config.get("app_authentication", "token_validity_period")
        self.refresh_token_validity_period = self.config.get("app_authentication", "refresh_token_validity_period")
        self.app_secret_dict = convert_str_to_dict(self.config.get("app_authentication", "app_secret_map"))

    def get_tokens(self, request: Request):
        grant_type = request.query_params.get("grant_type", "")
        tokens = None
        if grant_type == "secret":
            app_id = request.query_params.get("app_id", "")
            app_secret = request.query_params.get("app_secret", "")
            tokens = self.create_tokens_by_secret(app_id, app_secret)
        elif grant_type == "refresh_token":
            refresh_token = request.query_params.get("refresh_token", "")
            tokens = self.create_tokens_by_refresh_token(refresh_token)
        else:
            return "Unsupported grant type."
        
        if isinstance(tokens, str):
            return tokens
        elif isinstance(tokens, list):
            res = {
                "token": tokens[0],
                "token_validity_period": self.token_validity_period,
                "refresh_token": tokens[1],
                "refresh_token_validity_period": self.refresh_token_validity_period
            }
            return res
        else:
            return "Gnerate token error."

    def create_tokens_by_secret(self, app_id, app_secret) -> list[str]:
        if not app_id or not app_secret:
            return "Please provide app id and secret."
        
        try:
            if not self._checkAppSecret(app_id, app_secret):
                return "App not exist or secret not correct."
            
            token = JwtTokenTool.create_token(app_id, app_secret, self.token_validity_period)
            refresh_token = JwtTokenTool.create_token(app_id, app_secret, self.refresh_token_validity_period)

            # save in redis
            token_key = self._get_md5(token)
            info = {
                "app_id": app_id
            }
            RedisConnector.put(token_key, str(info), self.token_validity_period)
            info["token_key"] = token_key
            RedisConnector.put(self._get_md5(refresh_token), str(info), self.refresh_token_validity_period)

            return [token, refresh_token]
        except Exception as e:
            logger.error("create tokens error. ", str(e))
            return None

    def create_tokens_by_refresh_token(self, refresh_token) -> list[str]:
        if not refresh_token:
            return "Please provide refresh_token."
        
        try:
            refresh_token_key = self._get_md5(refresh_token)
            info = RedisConnector.get(refresh_token_key)
            if not info:
                return "Refresh token is expired."

            info = eval(info)
            payload = JwtTokenTool.get_payload(refresh_token, info)
            if (isinstance(payload, str) and payload == "RSA key is expired.") \
                or int(payload['exp']) < int(time.time()):
                return "Refresh token is expired."

            token = JwtTokenTool.create_token(info['app_id'], self.app_secret_dict[info['app_id']], self.token_validity_period)
            refresh_token = JwtTokenTool.create_token(info['app_id'], self.app_secret_dict[info['app_id']], self.refresh_token_validity_period)

            # save in redis
            previous_token_key = info.pop('token_key')
            token_key = self._get_md5(token)
            RedisConnector.put(token_key, str(info), self.token_validity_period)
            info['token_key'] = token_key
            RedisConnector.put(self._get_md5(refresh_token), str(info), self.refresh_token_validity_period)

            # remove previous tokens
            RedisConnector.delete(refresh_token_key)
            RedisConnector.delete(previous_token_key)

            return [token, refresh_token]
        except Exception as e:
            logger.error("create tokens error. ", str(e))
            return None

    def validate(self, request: Request) -> str:
        token = request.headers.get("Authorization")
        if not token:
            return "Please provide token."
        try:
            token_key = self._get_md5(token)
            info = RedisConnector.get(token_key)
            if not info:
                return "Token is expired."
            
            info = eval(info)
            payload = JwtTokenTool.get_payload(token, info)
            if (isinstance(payload, str) and payload == "RSA key is expired.") \
                or int(payload['exp']) < int(time.time()):
                return "Token is expired."

            return "success"

        except Exception as e:
            logger.error("create tokens error. ", str(e))
            return "Validate token error."

    def _checkAppSecret(self, app_id, app_secret):
        for id, secret in self.app_secret_dict.items():
            if app_id == id and app_secret == secret:
                return True

        return False
    
    def _get_md5(self, msg):
        md5 = hashlib.md5()
        md5.update(msg.encode('utf-8'))
        return md5.hexdigest()
