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

import json
from abc import abstractmethod
from fastapi import Request
from fastapi.responses import StreamingResponse, Response

from pilot.configs.model_config import config_parser

class BaseAuthenticator():
    '''
    use as decorator for interface authentication
    '''
    def __init__(self, func) -> None:
        self.config = config_parser
        self._func = func

    @abstractmethod
    def validate(self, request: Request) -> str:
        pass

    def error_template(self, msg):
        data = json.dumps({"answer": msg}, ensure_ascii=False)
        yield f"data: {data}\n\n"

    def __call__(self, request: Request):
        msg = self.validate(request)
        if msg != "success":
            ret = Response(msg)
            ret.status_code = 401
            return ret
        
        return self._func(request)
