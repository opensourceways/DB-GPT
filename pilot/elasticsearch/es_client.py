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
# Create: 2023/8/15

import json
import requests
import urllib3

from pilot.configs.model_config import config_parser
from pilot.logs import logger

urllib3.disable_warnings()

class ESClient(object):
    def __init__(self):
        self.configs = config_parser
        self.es_url = self.configs.get('elasticsearch', 'es_url')
        self.authorization = self.configs.get('elasticsearch', 'authorization')
        self.index_name = self.configs.get('elasticsearch', 'index_name')
        self.query = self.configs.get('elasticsearch', 'query')
        self.additional_path = self.configs.get('whitelist', 'additional_path')
        self.default_headers = {
            'Content-Type': 'application/json',
            'Authorization': self.authorization
        }
        self.whitelist_set = set()    

    def getSearchUrl(self, url=None, index_name=None):
        if index_name is None:
            index_name = self.index_name
        if url is None:
            url = self.es_url
        return f"{url}/{index_name}/_search"

    
    def search_keyword(self, term, context):
        search_json = self.query % (term, context)
        res = requests.post(self.getSearchUrl(), data=search_json.encode('utf-8'), headers=self.default_headers, verify=False)

        if res.status_code != 200:
            return False
        if res.json()['hits']['hits']:
            return True
        return False

    def check_whitelist(self, query):
        tokens = self.analyze(query)
        words = []
        with open(self.additional_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in lines:
                words.extend(line.split(','))
        for token in tokens:
            if token.get('token') not in words:
                return False
        return True

    def update_whitelist(self, query):
        self.get_all_docs(query)
        self.additional_whitelist()

        with open(self.additional_path, 'w', encoding='utf-8') as file:
            for item in self.whitelist_set:
                file.write(item + ',')
        self.whitelist_set = set()
    
    def additional_whitelist(self):
        try:
            with open(self.additional_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                for line in lines:
                    self.whitelist_set.add(line.strip())
        except FileNotFoundError as e:
            logger.info("no additional whitelist")
    
    def get_all_docs(self, query):
        search = {
            "size": 1000,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "query_string": {
                                "analyze_wildcard": True,
                                "query": query
                            }
                        }
                    ]
                }
            }
        }
        self.scrollSearch(search=json.dumps(search), func=self.get_token_func)

    def get_token_func(self, hit):
        for data in hit:
            text = data['_source']['textContent']
            tokens = self.analyze(text)
            if not tokens:
                continue
            self.whitelist(tokens)

    def whitelist(self, tokens):
        for token in tokens:
            token = str(token.get('token'))
            self.whitelist_set.add(token)

    def analyze(self, text, analyzer="ik_smart"):
        url = self.es_url + '/' + self.index_name + '/_analyze'
        body = {
            "analyzer": analyzer,
            "text": text
        }
        res = requests.get(url=url, headers=self.default_headers, data=json.dumps(body), verify=False, timeout=60)
        tokens = res.json().get('tokens')
        return tokens 

    def scrollSearch(self, search=None, scroll_duration='1m', func=None):
        url = self.es_url + '/' + self.index_name + '/_search?scroll=' + scroll_duration
        res = requests.get(url=url, headers=self.default_headers, data=search.encode('utf-8'), verify=False, timeout=60)
        if res.status_code != 200:
            logger.info('requests error')
            return
        res_data = res.json()
        data = res_data['hits']['hits']
        logger.info('scroll data count: %s' % len(data))
        func(data)

        scroll_id = res_data['_scroll_id']
        while scroll_id is not None and len(data) != 0:
            url = self.es_url + '/_search/scroll'
            search = '''{
                          "scroll": "%s",
                          "scroll_id": "%s"
                        }''' % (scroll_duration, scroll_id)
            res = requests.get(url=url, headers=self.default_headers, data=search.encode('utf-8'), verify=False, timeout=60)
            if res.status_code != 200:
                logger.info('requests error')
                return
            res_data = res.json()
            scroll_id = res_data.get('_scroll_id')
            data = res_data['hits']['hits']
            logger.info('scroll data count: %s' % len(data))
            func(data)
        logger.info('scroll over')

