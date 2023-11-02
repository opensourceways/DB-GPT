#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import time
import redis

from pilot.configs.model_config import config_parser, raw_config_parser
from pilot.logs import logger

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
    def put(cls, key, value, period, max_retries=3, retry_interval=5):
        for _ in range(max_retries):
            try:
                cls.redis.setex(name=key, value=value, time=period)
                return
            except redis.ConnectionError as e:
                logger.info(f"Set operation failed, error: {e}. Retrying...")
                time.sleep(retry_interval)     
        logger.info(f"Set operation failed after {max_retries} retries.")

    @classmethod
    def get(cls, key, max_retries=3, retry_interval=5):
        for _ in range(max_retries):
            try:
                return cls.redis.get(key)
            except redis.ConnectionError as e:
                logger.info(f"Get operation failed, error: {e}. Retrying...")
                time.sleep(retry_interval)     
        logger.info(f"Get operation failed after {max_retries} retries.")

    @classmethod
    def delete(cls, key):
        cls.redis.delete(key)
