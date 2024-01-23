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

from urllib.parse import quote_plus as urlquote
from typing import Dict, Iterator, Any, AsyncGenerator

from pilot.configs.model_config import (
    DATASTORE_HOST,
    DATASTORE_DBNAME,
    DATASTORE_USERNAME,
    DATASTORE_PASSWORD,
    VECTORSTORE_HOST,
    VECTORSTORE_PORT,
    VECTORSTORE_DBNAME,
    VECTORSTORE_USERNAME,
    VECTORSTORE_PASSWORD,
    EMBEDDING_MODEL_PATH
)
from pilot.model.base import ModelOutput

from gptcache.adapter.adapter import adapt
from gptcache.adapter.api import init_similar_cache
from gptcache.core import Cache
from gptcache.manager.scalar_data.base import Answer, DataType
from gptcache.manager import manager_factory
from gptcache.embedding import Huggingface
from gptcache.similarity_evaluation import ExactMatchEvaluation
from gptcache.adapter.openai import ChatCompletion

DEFAULT_QUESTION = [
    {
        "role": "user",
        "content": "hello"
    }
]

# data processor for baichuan model
class BaichuanDataProcessor:
    @staticmethod
    def get_prompt(data: Dict[str, Any], **_: Dict[str, Any]) -> Any:
        return data.get("messages")[-1].get("content")

    class AsyncIteratorWrapper:
        def __init__(self, obj):
            self._it = obj

        def __aiter__(self):
            return self
        
        async def __anext__(self):
            try:
                value = next(self._it)
            except StopIteration:
                raise StopAsyncIteration
            return value

    @staticmethod
    def cache_data_convert(cache_data):
        res = []
        cache_resp = ModelOutput(error_code=0, text=cache_data)
        res.append(cache_resp)
        res = iter(res)
        return BaichuanDataProcessor.AsyncIteratorWrapper(res)

    @staticmethod
    def get_stream_message_from_openai_answer(item):
        return item.text

# cache init
cache = Cache()
mysql_url = f"mysql+pymysql://{DATASTORE_USERNAME}:{urlquote(DATASTORE_PASSWORD)}@{DATASTORE_HOST}:3306/{DATASTORE_DBNAME}"
postgres_url = f"postgresql://{VECTORSTORE_USERNAME}:{urlquote(VECTORSTORE_PASSWORD)}@{VECTORSTORE_HOST}:{VECTORSTORE_PORT}/{VECTORSTORE_DBNAME}"
embedding_model=Huggingface(EMBEDDING_MODEL_PATH)
generator_type = BaichuanDataProcessor
init_similar_cache(
    cache_obj=cache,
    pre_func=generator_type.get_prompt,
    data_manager=manager_factory(
        "mysql,pgvector",
        vector_params={
            "dimension": embedding_model.dimension,
            "url": postgres_url
        },
        scalar_params={"sql_url": mysql_url}
    ),
    embedding=embedding_model,
    evaluation=ExactMatchEvaluation()
)

def update_cache_callback(llm_data, update_cache_func, *args, **kwargs):
    if isinstance(llm_data, AsyncGenerator):

        async def hook_openai_data(it):
            total_answer = ""
            async for item in it:
                total_answer += generator_type.get_stream_message_from_openai_answer(item)
                yield item
            update_cache_func(Answer(total_answer, DataType.STR))

        return hook_openai_data(llm_data)
    elif not isinstance(llm_data, Iterator):
        update_cache_func(
            Answer(llm_data, DataType.STR)
        )
        return llm_data
    else:

        def hook_openai_data(it):
            total_answer = ""
            for item in it:
                total_answer += generator_type.get_stream_message_from_openai_answer(item)
                yield item
            update_cache_func(Answer(total_answer, DataType.STR))

        return hook_openai_data(llm_data)

def generate_stream_with_cache(func, *args, **kwargs):
    if kwargs.get("use_openai", False):
        return ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=kwargs.get("messages", DEFAULT_QUESTION),
            stream=True,
            cache_obj=cache
        )
    else:
        return adapt(
            func,
            generator_type.cache_data_convert,
            update_cache_callback,
            *args,
            cache_obj=cache,
            **kwargs
        )
