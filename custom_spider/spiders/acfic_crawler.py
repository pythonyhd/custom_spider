# -*- coding: utf-8 -*-
import ast
import json
import logging

import redis
import scrapy

from custom_spider import settings
from custom_spider.config import acfic_settings
from custom_spider.utils.bloomfilter import BloomFilter

logger = logging.getLogger(__name__)


class AcficCrawlerSpider(scrapy.Spider):
    name = 'acfic_crawler'
    allowed_domains = ['acfic.org.cn']
    search_url = 'http://www.acfic.org.cn/shixin/new/SearchActionAll'

    # redis 搜索关键词
    redis_keyword = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB
    )
    reids_name = name + ':keywords'

    # 布隆过滤器-用来过滤关键词(该关键词没有搜索结果，可以抛弃)
    bloomfilter_client = BloomFilter(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
        blockNum=1,
        key=name + ":bloomfilter"
    )

    custom_settings = acfic_settings

    def start_requests(self):
        """搜索入口函数"""
        # keywords = ['北京', '马俊华', '张婧']
        # for keyword in keywords:
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            form_data = {
                "iname": str(keyword),
                "code": "",
                "areaid": "0",
                "page": "1",
                "rows": "10",
            }
            meta_data = {'keyword': keyword, 'form_data': form_data}
            yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data)

    def parse(self, response):
        """解析数据，翻页请求"""
        form_data = response.meta.get('form_data')
        keyword = response.meta.get('keyword')
        # 解析
        results = ast.literal_eval(response.body_as_unicode())
        rows = results.get('rows')
        if not rows:
            return
        for data in rows:
            iname = data.get('iname')  # 被执行人姓名／名称
            case_code = data.get('case_code')  # 案号
            gist_cid = data.get('gist_cid')  # 执行依据文号
            court_name = data.get('court_name')  # 执行法院
            gist_nuit = data.get('gist_nuit')  # 做出执行依据单位/法院名
            cardnum = data.get('cardnum')  # 身份证号／组织机构代码
            area_name = data.get('area_name')  # 省份
            age = data.get('age')  # 年龄
            sex_name = data.get('sex_name')  # 性别
            duty = data.get('duty')  # 生效法律文书确定的义务
            disreput_type_name = data.get('disreput_type_name')  # 失信被执行人行为具体情形
            performance = data.get('performance')  # 被执行人的履行情况
            publish_date = data.get('publish_date')  # 发布时间
            reg_date = data.get('reg_date')  # 立案时间
            buesinessentity = data.get('buesinessentity')  # 法人
            unperformed_part = data.get('unperformed_part')  # 执行标的
            area_id = data.get('area_id')  # 地区编码标识
            # cardtype = jsonpath.jsonpath(results, expr='$.rows[*].cards[*].cardtype')
            # id = jsonpath.jsonpath(results, expr='$.rows[*].cards[*].id')
            item = dict(
                oname=iname, pname=buesinessentity, area_name=area_name, uccode=cardnum, sex_name=sex_name,
                age=age, court_name=court_name, gist_cid=gist_cid, case_code=case_code, gist_nuit=gist_nuit,
                reg_date=reg_date, publish_date=publish_date, performance=performance, duty=duty,
                disreput_type_name=disreput_type_name, unperformed_part=unperformed_part, area_id=area_id,
                xq_url=response.url, content=json.dumps(data, ensure_ascii=False), keyword=keyword,
            )
            yield item

        # 翻页请求
        total = results.get('total')  # 总数
        if int(total) == 0:
            if self.bloomfilter_client.is_exist(keyword):
                logger.info(f"{keyword}--- 没有搜索结果并且被过滤了")
            else:
                logger.debug(f"该搜索词没有搜索结果--{keyword}--添加到布隆过滤器")
                self.bloomfilter_client.add(keyword)
        else:
            pages = int(int(total) / 10) + 1  # 总页数
            is_first = response.meta.get('is_first', True)
            if is_first:
                for page in range(2, pages + 1):
                    form_data['page'] = str(page)
                    meta_data = {'is_first': False, 'keyword': keyword, 'form_data': form_data}
                    yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data)