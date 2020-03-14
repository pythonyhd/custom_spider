# -*- coding: utf-8 -*-
from scrapy import cmdline


# 中国执行信息公开网-失信被执行人
# cmdline.execute('scrapy crawl promise_crawler'.split())
# 中国执行信息公开网-被执行人
# cmdline.execute('scrapy crawl execute_crawler'.split())
# 中国执行信息公开网-限制高消费
# cmdline.execute('scrapy crawl consumption_crawler'.split())
# 中华全国工商业联合会-失信被执行人
cmdline.execute('scrapy crawl acfic_crawler'.split())