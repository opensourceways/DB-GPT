#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import redis

from pilot.configs.model_config import config_parser, raw_config_parser

class RedisConnector:
    """RedisConnector"""
    
    redis = redis.Redis(
        host=config_parser.get('redis', 'redis_host'),
        port=config_parser.get("redis", "redis_port"),
        password=raw_config_parser.get("redis", "redis_password"),
        db=config_parser.get("redis", "redis_db"),
        encoding="utf-8",
        decode_responses=True
    )

    @classmethod
    def put(cls, key, value, period):
        cls.redis.setex(name=key, value=value, time=period)

    @classmethod
    def get(cls, key):
        return cls.redis.get(key)

    @classmethod
    def delete(cls, key):
        cls.redis.delete(key)
