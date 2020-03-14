# -*- coding: utf-8 -*-


# 中国执行信息公开网-失信被执行人-配置信息
shixin_custom_settings ={
    "RETRY_ENABLED": True,
    "RETRY_TIMES": '9',
    "DOWNLOAD_TIMEOUT": '15',

    "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
    "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
    "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
    "SCHEDULER_PERSIST": True,

    "ITEM_PIPELINES": {
        'custom_spider.pipelines.CustomSpiderPipeline': 300,
        'custom_spider.pipelines.MongodbIndexPipeline': 320,
        # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
    },

    'DOWNLOADER_MIDDLEWARES': {
        'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
        'custom_spider.middlewares.RandomProxyMiddlerware': 440,
        'custom_spider.middlewares.CheckResponseMiddleware': 460,
        'custom_spider.middlewares.RewriteRetryMiddleware': 480,
    },
}


# 中国执行信息公开网-被执行人-配置信息
execute_custom_settings ={
    "RETRY_ENABLED": True,
    "RETRY_TIMES": '9',
    "DOWNLOAD_TIMEOUT": '15',

    "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
    "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
    "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
    "SCHEDULER_PERSIST": True,

    "ITEM_PIPELINES": {
        'custom_spider.pipelines.CustomSpiderPipeline': 300,
        'custom_spider.pipelines.MongodbIndexPipeline': 320,
        # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
    },

    'DOWNLOADER_MIDDLEWARES': {
        'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
        'custom_spider.middlewares.RandomProxyMiddlerware': 440,
        'custom_spider.middlewares.CheckEcecuteMiddleware': 460,
        'custom_spider.middlewares.RewriteRetryMiddleware': 480,
    },
}


# 中国执行信息公开网-限制高消费-配置信息
consumption_settings = {
    "RETRY_ENABLED": True,
    "RETRY_TIMES": '2',
    "DOWNLOAD_TIMEOUT": '10',
    # "DOWNLOAD_DELAY": '1',

    "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
    "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
    "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
    "SCHEDULER_PERSIST": True,

    "ITEM_PIPELINES": {
        'custom_spider.pipelines.CustomSpiderPipeline': 300,
        'custom_spider.pipelines.DownloadFilesPipeline': 320,
        'custom_spider.pipelines.MongodbIndexPipeline': 340,
        # 'custom_spider.pipelines.MysqlTwistedPipeline': 360,
    },

    'DOWNLOADER_MIDDLEWARES': {
        'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
        # 'custom_spider.middlewares.CloudProxyMiddleware': 440,
        'custom_spider.middlewares.ChechConsumMiddleware': 460,
    },

    'DEFAULT_REQUEST_HEADERS': {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "zxgk.court.gov.cn",
        "Origin": "http://zxgk.court.gov.cn",
        "X-Requested-With": "XMLHttpRequest",
    }
}


# 中华全国工商业联合会-失信被执行人
acfic_settings = {
    "REDIRECT_ENABLED": False,
    "RETRY_ENABLED": True,
    "RETRY_TIMES": '9',
    "DOWNLOAD_TIMEOUT": '20',
    "DOWNLOAD_FAIL_ON_DATALOSS": False,

    "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
    "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
    "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
    "SCHEDULER_PERSIST": True,
    # "REDIS_URL": "redis://localhost:6379/4",
    # "SCHEDULER_FLUSH_ON_START": True,  # 是否在开始之前清空，调度器和去重记录

    "ITEM_PIPELINES": {
        'custom_spider.pipelines.CustomSpiderPipeline': 300,
        'custom_spider.pipelines.MongodbIndexPipeline': 340,
    },

    'DOWNLOADER_MIDDLEWARES': {
        'custom_spider.middlewares.RandomUserAgentMiddleware': 420,
        'custom_spider.middlewares.RandomProxyMiddlerware': 440,
        'custom_spider.middlewares.RewriteRetryMiddleware': 460,
    }
}