# -*- coding: utf-8 -*-

BOT_NAME = 'custom_spider'

SPIDER_MODULES = ['custom_spider.spiders']
NEWSPIDER_MODULE = 'custom_spider.spiders'

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
scrapy 基本配置
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
ROBOTSTXT_OBEY = False
LOG_LEVEL = "INFO"
# 验证码识别接口
CAPTCH_URI = 'http://127.0.0.1:7788'

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
数据存储 相关配置
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# 存储到mongodb
MONGO_URI = '127.0.0.1'
MONGO_DATA_BASE = 'factminr_spider'
# 存储到MySQL
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = '123456'
DB_NAME = 'factminr_spider'
DB_CHARSET = 'utf8'

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
redis 相关配置
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# redis 基础配置
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = ""
REDIS_DB = 4
REDIS_PARAMS = {
    "password": "",
    "db": 4,
}
# redis 代理池配置
REDIS_PROXIES_HOST = '117.78.35.12'
REDIS_PROXIES_PORT = 6379
REDIS_PROXIES_PASSWORD = ''
REDIS_PROXIES_DB = 15

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
scrapy 请求头
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
RANDOM_UA_TYPE = "random"