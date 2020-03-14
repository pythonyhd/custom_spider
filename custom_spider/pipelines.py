# -*- coding: utf-8 -*-
import json
import logging
import os
import time

import pymongo
import pymysql
import redis
import scrapy
from scrapy.exceptions import DropItem
from scrapy.pipelines.files import FilesPipeline
from twisted.enterprise import adbapi

from custom_spider import settings

logger = logging.getLogger(__name__)


class CustomSpiderPipeline(object):
    """添加必要字段"""
    def process_item(self, item, spider):
        item['spider_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))  # 抓取时间
        item['spider_name'] = spider.name
        item['process_status'] = 0
        item['upload_status'] = 0
        item['alter_status'] = 0
        return item


class MongodbIndexPipeline(object):
    """存储到mongodb数据库并且创建索引"""
    def __init__(self, mongo_uri, mongo_db):
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[mongo_db]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGODB_HOST'),
            mongo_db=crawler.settings.get('MONGODB_NAME')
        )

    def process_item(self, item, spider):
        collection = self.db[spider.name]
        collection.create_index([('oname', 1), ('uccode', -1)])  # 1表示升序，-1降序
        try:
            collection.insert(dict(item))
        except:
            logger.info('数据重复')
        return item


class DownloadFilesPipeline(FilesPipeline):
    """文件下载管道"""
    def get_media_requests(self, item, info):
        file_url = item.get('file_url')
        keyword = item.get('keyword')
        if file_url:
            yield scrapy.Request(url=file_url, meta={'keyword': keyword})

    def file_path(self, request, response=None, info=None):
        # 文件夹名称
        file_name = request.meta.get('keyword')
        if not file_name:
            os.makedirs(file_name)
        # 文件名称
        pdf_name = request.url.split('/')[-1]
        files = u'{0}/{1}'.format(file_name, pdf_name)
        return files

    def item_completed(self, results, item, info):
        file_paths = [x['path'] for ok, x in results if ok]
        if file_paths:
            item['file_path'] = file_paths[0]
        else:
            item['file_path'] = ''
        return item


class MysqlTwistedPipeline(object):
    """异步存储到MySQL数据库"""
    def __init__(self, dbpool):
        self.dbpool = dbpool
        self.redis_client = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
        )

    @classmethod
    def from_crawler(cls, crawler):
        dbparms = dict(
            host=crawler.settings.get('MYSQL_HOST'),
            port=crawler.settings.get('MYSQL_PORT'),
            user=crawler.settings.get('MYSQL_USER'),
            passwd=crawler.settings.get('MYSQL_PASSWORD'),
            db=crawler.settings.get('MYSQL_NAME'),
            charset=crawler.settings.get('MYSQL_CHARSET'),
            cursorclass=pymysql.cursors.Cursor,
            use_unicode=True,
            connect_timeout=600,  # 分钟，默认十分钟不操作断开
        )
        dbpool = adbapi.ConnectionPool('pymysql', **dbparms)  # 连接
        return cls(dbpool)

    def process_item(self, item, spider):
        self.dbpool.runInteraction(self.process_insert, item)  # 调用twisted进行异步的插入操作

    def process_insert(self, cursor, item):
        table = item.get('spider_name')
        fields = ", ".join(list(item.keys()))
        sub_char = ", ".join(["%s"] * len(item))
        values = tuple(list(item.values()))
        # sql = "insert into {}({}) values ({})".format(table, fields, sub_char)
        sql = "insert into %s(%s) values (%s)" % (table, fields, sub_char)

        try:
            cursor.execute(sql, values)
        except Exception as e:
            if "Duplicate" in repr(e):
                logger.info("数据重复--删除")
                DropItem(item)
            else:
                logger.info('插入失败--{}'.format(repr(e)))
                self.redis_client.sadd("trafic:error_items", json.dumps(dict(item), ensure_ascii=False))