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
# Create: 2023/9/15

from ast import Dict
from dataclasses import asdict, dataclass, field
from threading import Thread
from types import MethodType
from typing import Any, List, Optional, Tuple, Union
import re

import torch
from transformers import PreTrainedModel, TextIteratorStreamer

from transformers import (
    LogitsProcessor,
    LogitsProcessorList,
    StoppingCriteria,
    StoppingCriteriaList
)
from pilot.logs import logger

from pilot.scene.base_message import ModelMessage, _parse_model_messages

_CHATGLM_SEP = "\n"
_CHATGLM2_SEP = "\n\n"


@torch.inference_mode()
def baichuan_generate_stream(
    model, tokenizer, params, device, context_len=2048, stream_interval=2
) :

    """Generate text using baichuan model"""
    tokenizer.eos_token = "<reserved_102>"
    tokenizer.add_special_tokens(dict(additional_special_tokens=["<reserved_102>"]))

    messages: List[ModelMessage] = params["messages"]
    query, system_messages, history = _parse_model_messages(messages)
    logger.info(f"********************     query = {query}")

    gen_kwargs, _ = process_args(query, params, device, tokenizer)

    streamer = TextIteratorStreamer(tokenizer, timeout=60.0, skip_prompt=True, skip_special_tokens=True)
    gen_kwargs["streamer"] = streamer

    model.generate = MethodType(PreTrainedModel.generate, model)
    thread = Thread(target=model.generate, kwargs=gen_kwargs)
    thread.start()

    yield from streamer

def process_args(prompt, params, device, tokenizer):
    input_ids = tokenizer(prompt).input_ids
    if tokenizer.bos_token_id:
        bos_ids = [tokenizer.bos_token_id] + [tokenizer.convert_tokens_to_ids("<reserved_102>")]
    else:
        bos_ids = []

    if tokenizer.eos_token_id:
        eos_ids = [tokenizer.eos_token_id]
    else:
        raise ValueError("EOS token is required.")
    input_ids = bos_ids + input_ids + eos_ids
    input_ids = torch.tensor([input_ids], device=device)
    prompt_length = len(input_ids[0])
    
    temperature = float(params.get("temperature", 0.01))
    top_k = params.get("top_k")
    top_p = params.get("top_p")
    max_new_tokens = params.get("max_new_tokens")

    generating_args = GeneratingArguments()
    gen_kwargs = generating_args.to_dict()
    gen_kwargs.update(dict(
        input_ids=input_ids,
        temperature=temperature or gen_kwargs["temperature"],
        top_p=top_p or gen_kwargs["top_p"],
        top_k=top_k or gen_kwargs["top_k"],
        logits_processor=get_logits_processor(),
        stopping_criteria=get_stopping_criteria(tokenizer.additional_special_tokens_ids)
    ))

    if max_new_tokens:
        gen_kwargs.pop("max_length", None)
        gen_kwargs["max_new_tokens"] = max_new_tokens

    return gen_kwargs, prompt_length


class InvalidScoreLogitsProcessor(LogitsProcessor):

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        if torch.isnan(scores).any() or torch.isinf(scores).any():
            scores.zero_()
            scores[..., 0] = 1.0
        return scores


def get_logits_processor() -> LogitsProcessorList:
    logits_processor = LogitsProcessorList()
    logits_processor.append(InvalidScoreLogitsProcessor())
    return logits_processor


class StopWordsCriteria(StoppingCriteria):

    def __init__(self, stop_ids: List[int]) -> None:
        super().__init__()
        self.stop_ids = stop_ids

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        return any([stop_id in input_ids[:, -1] for stop_id in self.stop_ids])


def get_stopping_criteria(stop_ids: List[int]) -> StoppingCriteriaList:
    stopping_criteria = StoppingCriteriaList()
    stopping_criteria.append(StopWordsCriteria(stop_ids))
    return stopping_criteria

@dataclass
class GeneratingArguments:
    r"""
    Arguments pertaining to specify the decoding parameters.
    """
    do_sample: Optional[bool] = field(
        default=True,
        metadata={"help": "Whether or not to use sampling, use greedy decoding otherwise."}
    )
    temperature: Optional[float] = field(
        default=0.95,
        metadata={"help": "The value used to modulate the next token probabilities."}
    )
    top_p: Optional[float] = field(
        default=0.7,
        metadata={"help": "The smallest set of most probable tokens with probabilities that add up to top_p or higher are kept."}
    )
    top_k: Optional[int] = field(
        default=50,
        metadata={"help": "The number of highest probability vocabulary tokens to keep for top-k filtering."}
    )
    num_beams: Optional[int] = field(
        default=1,
        metadata={"help": "Number of beams for beam search. 1 means no beam search."}
    )
    max_length: Optional[int] = field(
        default=None,
        metadata={"help": "The maximum length the generated tokens can have. It can be overridden by max_new_tokens."}
    )
    max_new_tokens: Optional[int] = field(
        default=512,
        metadata={"help": "The maximum numbers of tokens to generate, ignoring the number of tokens in the prompt."}
    )
    repetition_penalty: Optional[float] = field(
        default=1.0,
        metadata={"help": "The parameter for repetition penalty. 1.0 means no penalty."}
    )
    length_penalty: Optional[float] = field(
        default=1.0,
        metadata={"help": "Exponential penalty to the length that is used with beam-based generation."}
    )

    def to_dict(self):
        args = asdict(self)
        if args.get("max_new_tokens", None):
            args.pop("max_length", None)
        return args

