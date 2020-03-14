# -*- coding: utf-8 -*-
import ast
import json
import logging
import time

import jsonpath
import redis
import scrapy

from custom_spider import settings
from custom_spider.config import execute_custom_settings
from custom_spider.utils.bloomfilter import BloomFilter
from custom_spider.work_utils.process_captcha import ExecuteCaptchaProcess

logger = logging.getLogger(__name__)


class ExecuteCrawlerSpider(scrapy.Spider):
    name = 'execute_crawler'
    allowed_domains = ['zxgk.court.gov.cn']
    search_url = 'http://zxgk.court.gov.cn/zhixing/searchBzxr.do'  # 被执行人搜索列表
    exe_cap = ExecuteCaptchaProcess()
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

    custom_settings = execute_custom_settings

    def start_requests(self):
        """ 被执行人搜索接口，请求列表第一页，换一个搜索词换一张图片 """
        # keywords = ['张婧', '马俊华', '于华东', '北京']
        # for keyword in keywords:
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            captcha_item = self.exe_cap.main()
            pCode = captcha_item.get("code")
            captchaId = captcha_item.get('captchaId')
            form_data = {
                "pName": str(keyword),
                "pCardNum": "",
                "selectCourtId": "0",
                "pCode": str(pCode),
                "captchaId": str(captchaId),
                "searchCourtName": "全国法院（包含地方各级法院）",
                "selectCourtArrange": "1",
                "currentPage": "1",
            }
            meta_data = {'keyword': keyword, 'pCode': pCode, 'captchaId': captchaId, 'form_data': form_data}
            yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data)

    def parse(self, response):
        """解析列表第一页，列表页翻页"""
        keyword = response.meta.get('keyword')
        pCode = response.meta.get('pCode')
        captchaId = response.meta.get('captchaId')
        form_data = response.meta.get('form_data')
        # 列表解析
        # resp_list = ast.literal_eval(response.text)
        results = json.loads(response.body_as_unicode())
        if not results:
            return None
        totalSize = jsonpath.jsonpath(results, expr='$..totalSize')
        if int(totalSize[0]) == 0:
            if self.bloomfilter_client.is_exist(keyword):
                logger.info(f"{keyword}--- 没有搜索结果并且被过滤了")
            else:
                logger.debug(f"该搜索词没有搜索结果--{keyword}--添加到布隆过滤器")
                self.bloomfilter_client.add(keyword)
        else:
            for data in results[0].get('result'):
                id = data.get('id')
                # 请求详情页
                url = 'http://zxgk.court.gov.cn/zhixing/newdetail?id={}&j_captcha={}&captchaId={}&_={}'.format(id, pCode, captchaId, int(round(time.time() * 1000)))
                yield scrapy.Request(url=url, meta={'keyword': keyword}, callback=self.parse_detail, priority=5)

            # 列表翻页
            totalPage = results[0].get('totalPage')  # 总页数
            cuur_page = response.meta.get('cuur_page', 1)
            if cuur_page < int(totalPage):
                cuur_page += 1
                logger.info(f'开始请求第:{cuur_page}页--搜索词:{keyword}')
                form_data['currentPage'] = str(cuur_page)
                meta_data = {'cuur_page':cuur_page, 'keyword': keyword, 'pCode': pCode, 'captchaId': captchaId, 'form_data': form_data}
                yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data, priority=3)

    def parse_detail(self, response):
        """ 解析详情页 """
        keyword = response.meta.get('keyword')  # 存储keyword去数据库对比，关键词抓取条数跟网站是否一致
        # 解析
        results = json.loads(response.text)
        caseCode = results.get('caseCode', '')  # 案号
        pname = results.get('pname', '')  # 被执行人姓名/名称
        sexname = results.get('sexname', '')  # 性别
        partyCardNum = results.get('partyCardNum', '')  # 身份证号码/组织机构代码
        execCourtName = results.get('execCourtName', '')  # 执行法院
        caseCreateTime = results.get('caseCreateTime', '')  # 立案时间
        gistId = results.get('gistId', '')  # 执行文号
        execMoney = results.get('execMoney', '')  # 执行标的
        item = dict(
            caseCode=caseCode, pname=pname, sexname=sexname, partyCardNum=partyCardNum,
            execCourtName=execCourtName, caseCreateTime=caseCreateTime, gistId=gistId,
            execMoney=execMoney, url=response.url, keyword=keyword,
            content=json.dumps(results, ensure_ascii=False)
        )
        yield item

    @classmethod
    def process_erro_keyword(cls, keyword):
        with open('error_keyword.txt', 'wb') as f:
            f.write(keyword)