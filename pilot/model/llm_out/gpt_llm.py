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
# Create: 2023/10/10

import json
import time
import openai
from pilot.configs.model_config import config_parser
from pilot.logs import logger

openai.api_key = config_parser.get('gpt', 'openai_key')
retry_time = config_parser.get('gpt', 'retry_time')
retry_interval = config_parser.get('gpt', 'retry_interval')

messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": "Where was it played?"}
    ]

fun_num = 0


def retry_handler(func):
    def warp(*args, **kwargs):
        global fun_num
        try:
            if args[len(args) - 1] != "retry":
                fun_num = 0

            newarg = []
            for i in args:
                if i != 'retry':
                    newarg.append(i)
            response = func(*newarg, **kwargs)
        except (openai.error.APIError, openai.error.ServiceUnavailableError, openai.error.Timeout) as ex:
            while fun_num < retry_time:
                try:
                    fun_num += 1
                    logger.info("retry " + str(func.__name__) + ":" + str(fun_num) + "次")
                    logger.info("openai error:" + str(ex))
                    time.sleep(retry_interval)
                    if 'retry' not in args:
                        response = warp(*args, "retry", **kwargs)
                    else:
                        response = warp(*args, **kwargs)
                    return response
                finally:
                    pass
        except Exception as e:
            logger.info(
                "retry_handler Exception: fetch error :" + str(e) + "retry " + str(func.__name__) + ":" + str(
                    fun_num) + " Count")
            raise e
        else:
            logger.info("retry_handler else: check response instance. " + "retry " + str(func.__name__) + ":" + str(
                fun_num) + "次")

            fun_num = 0
            logger.info("retry_handler else: success")
            return response

    return warp


@retry_handler
def chat_gpt(messages, model="gpt-3.5-turbo", stream=False):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        stream=stream
    )
    response = response['choices'][0]['message']['content']
    return response


@retry_handler
def chat_gpt_stream(messages, model="gpt-3.5-turbo", stream=True):
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        stream=stream
    )
    for chunk in response:
        content = ''
        if "content" in chunk["choices"][0]["delta"]:
            content = chunk["choices"][0]["delta"]["content"]
            data = json.dumps({"answer": content}, ensure_ascii=False)
            yield f"data: {data}\n"