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
# Create: 2023/9/4

import requests
import json
from fastapi import Request
from fastapi.responses import StreamingResponse

from pilot.configs.model_config import config_parser
from pilot.logs import logger
from pilot.authenticaton.base_authenticator import BaseAuthenticator

class OneidUserAuthenticator(BaseAuthenticator):
    def get_manage_token(self) -> str:
        manage_endponit = self.config.get('oneid_user_authentication', 'manage_endponit')
        app_id = self.config.get('oneid_user_authentication', 'app_id')
        app_secret = self.config.get('oneid_user_authentication', 'app_secret')
        headers = {
            "Content-Type": "application/json"
        }
        body = json.dumps({
            "grant_type": "token",
            "app_id": app_id,
            "app_secret": app_secret
        })

        try:
            rs = requests.post(manage_endponit, headers=headers, data=body)
            if rs.status_code == 200:
                manager_token = eval(rs.text)['token']
                return manager_token
        except Exception as e:
            print("Error: get management token fail. ", e)
            return ""

    def validate(self, request: Request) -> str:
        token = request.headers.get("Authorization")
        logger.info(f"************ get token {token} *************")
        cookie_UT = request.cookies.get("_U_T_")
        logger.info(f"************ get token {cookie_UT} *************")
        cookie_YG = request.cookies.get("_Y_G_")
        logger.info(f"************ get token {cookie_YG} *************")
        if not token or not cookie_UT or not cookie_YG:
            return "Unauthorized, please ensure that you have logged in."
        
        manager_token = self.get_manage_token()
        if not manager_token:
            return "Unauthorized, please contact administrator."

        valid_endponit = self.config.get('oneid_user_authentication', 'oneid_user_endpoint')
        headers = {
            "token": manager_token,
            "user-token": token,
        }
        cookies = {
            "_U_T_": cookie_UT,
            "_Y_G_": cookie_YG
        }
        try:
            rs = requests.get(valid_endponit, headers=headers, cookies=cookies)
            if rs.status_code == 200:
                if eval(rs.text)['data']['aigcPrivacyAccepted']:
                    return "success"
                else:
                    return "Unauthorized, please ensure that you have accepted privacy statement."
        except Exception as e:
            print("Error: validate token fail. ", e)

        return "Unauthorized, please ensure that you have logged in."
