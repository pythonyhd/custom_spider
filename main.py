# -*- coding: utf-8 -*-
from scrapy import cmdline


# 中国市场监管-行政处罚文书网
# cmdline.execute('scrapy crawl cfws_samr'.split())
# 中国执行信息公开网-限制高消费(需要超级稳定可用的代理IP，从请求验证码到详情页必须是同一个IP，否则请求不到)
# cmdline.execute('scrapy crawl xzgk_court'.split())
# 中国执行信息公开网-失信被执行人(除部分关键词可能翻页较多导致验证码失效进而翻页不全外，一切稳定运行)
cmdline.execute('scrapy crawl shixin_court'.split())