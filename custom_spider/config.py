# -*- coding: utf-8 -*-


# 中国执行信息公开网-限制高消费-配置信息
xzgxf_custom_settings = {
        # 大量请求验证码图片出现302，请求解析PDF也会出现302
        "HTTPERROR_ALLOWED_CODES": [302],
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        "DOWNLOAD_DELAY": '1',

        'DEFAULT_REQUEST_HEADERS': {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "zxgk.court.gov.cn",
            "Origin": "http://zxgk.court.gov.cn",
            "X-Requested-With": "XMLHttpRequest",
        },

        "ITEM_PIPELINES": {
            'custom_spider.pipelines.CustomSpiderPipeline': 300,
            'custom_spider.pipelines.MongodbIndexPipeline': 320,
            # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
        },

        'DOWNLOADER_MIDDLEWARES': {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            # 'custom_spider.middlewares.CloudProxyMiddleware': 440,  # 代理必须从头到尾是一个
            # 'custom_spider.middlewares.LocalRetryMiddlerware': 460,
        },

        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
        "SCHEDULER_PERSIST": True,
    }


# 中国执行信息公开网-失信被执行人-配置信息
shixin_custom_settings ={
        # 大量请求验证码图片出现302
        "HTTPERROR_ALLOWED_CODES": [302],
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        # "DOWNLOAD_DELAY": '1',

        "ITEM_PIPELINES": {
                    'custom_spider.pipelines.CustomSpiderPipeline': 300,
                    'custom_spider.pipelines.MongodbIndexPipeline': 320,
                    # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
        },

        'DOWNLOADER_MIDDLEWARES': {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            'custom_spider.middlewares.RandomProxyMiddlerware': 440,
            'custom_spider.middlewares.LocalRetryMiddlerware': 460,
        },

        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
        "SCHEDULER_PERSIST": True,
    }


# 中国市场监管-行政处罚文书网
xzcf_custom_settings = {
        "REDIRECT_ENABLED": False,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        # "DOWNLOAD_DELAY": '0.05',

        # "ITEM_PIPELINES": {
            # 'custom_spider.pipelines.CustomPipeline': 300,
            # 'custom_spider.pipelines.MongodbIndexPipeline': 320,
            # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
        # },

        "DOWNLOADER_MIDDLEWARES": {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            'custom_spider.middlewares.RandomProxyMiddlerware': 440,
            # 'custom_spider.middlewares.LocalRetryMiddlerware': 460,
        },
    }