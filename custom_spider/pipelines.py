# -*- coding: utf-8 -*-
import time

import pymongo


class CustomSpiderPipeline(object):
    """ 限制高消费-添加必要字段 """
    def process_item(self, item, spider):
        item['spider_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))  # 抓取时间
        item['process_status'] = 0
        item['upload_status'] = 0
        item['alter_status'] = 0
        return item


class MongodbIndexPipeline(object):
    """ 存储到mongodb数据库并且创建索引 """
    def __init__(self, mongo_uri, mongo_db):
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[mongo_db]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATA_BASE')
        )

    def process_item(self, item, spider):
        collection = self.db[spider.name]
        collection.create_index([('oname', 1), ('spider_time', -1)])  # 1表示升序，-1降序
        try:
            collection.insert(dict(item))
        except:
            from scrapy import log
            log.msg(message="dup key: {}".format(item["url"]), level=log.INFO)
        return item