# -*- coding: utf-8 -*-
import os

BOT_NAME = 'custom_spider'

SPIDER_MODULES = ['custom_spider.spiders']
NEWSPIDER_MODULE = 'custom_spider.spiders'

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
scrapy 基本配置
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
ROBOTSTXT_OBEY = False
LOG_LEVEL = "INFO"
RANDOM_UA_TYPE = "random"
# 验证码识别接口
CAPTCH_URI = 'http://127.0.0.1:7788'

project_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# 文件存储
FILES_STORE = os.path.join(project_path, 'files')  # 存储路径
FILES_EXPIRES = 90  # 失效时间

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
数据存储 相关配置
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
# 存储到mongodb
MONGODB_HOST = '127.0.0.1'
MONGODB_NAME = 'court_spider'  # 数据库名

# 存储到MySQL
MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_NAME = 'court_spider'  # 数据库名
MYSQL_CHARSET = 'utf8'

# redis 基础配置
REDIS_HOST = '127.0.0.1'
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