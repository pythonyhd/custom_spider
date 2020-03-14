# -*- coding: utf-8 -*-
import json
import logging

import jsonpath
import redis
import scrapy

from custom_spider import settings
from custom_spider.config import consumption_settings
from custom_spider.utils.bloomfilter import BloomFilter
from custom_spider.work_utils.process_captcha import ConsumptionCaptchaProcess

logger = logging.getLogger(__name__)


class ConsumptionCrawlerSpider(scrapy.Spider):
    name = 'consumption_crawler'
    allowed_domains = ['zxgk.court.gov.cn']
    cap = ConsumptionCaptchaProcess()
    search_url = 'http://zxgk.court.gov.cn/xgl/searchXgl.do'
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

    custom_settings = consumption_settings

    def start_requests(self):
        """限制高消费搜索入口"""
        # keywords = ['赵', '钱', '孙']
        # for keyword in keywords:
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            captcha_item = self.cap.main()
            pCode = captcha_item.get("code")
            captchaId = captcha_item.get('captchaId')
            proxy = captcha_item.get('proxy').get('http')
            form_data = {
                'pName': str(keyword),
                'pCardNum': "",
                'selectCourtId': '0',
                'pCode': str(pCode),  # 验证码识别结果
                'captchaId': str(captchaId),  # 验证码唯一标识
                'searchCourtName': '全国法院（包含地方各级法院）',
                'selectCourtArrange': '1',
                'currentPage': '1',  # 翻页参数
            }
            meta_data = {'keyword': keyword, 'proxy': proxy, 'pCode': pCode, 'captchaId': captchaId, 'form_data': form_data}
            yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data)

    def parse(self, response):
        """解析列表第一页，列表页翻页，列表请求错误显示（error验证码校验失败，重新刷验证码）"""
        keyword = response.meta.get('keyword')
        pCode = response.meta.get('pCode')
        captchaId = response.meta.get('captchaId')
        form_data = response.meta.get('form_data')
        proxy = response.meta.get('proxy')
        # 列表解析
        results = json.loads(response.text)
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
            for result in results[0].get('result'):
                AH = result.get('AH', '')  # 案号
                LASJStr = result.get('LASJStr', '')  # 立案时间
                XM = result.get('XM', '')  # 姓名主体
                QYXX = result.get('QYXX', '')  # 企业信息
                QY_MC = result.get('QY_MC', '')  # 企业名称
                QY_DM = result.get('QY_DM', '')  # 企业代码
                ZXFYDM = result.get('ZXFYDM', '')  # 年龄/或者是个编号
                ZXFYMC = result.get('ZXFYMC', '')  # 性别
                content = result.get('jsonObject', '')  # 数据字典
                FILEPATH = result.get('FILEPATH', '')  # PDF文件链接
                xq_url = 'http://zxgk.court.gov.cn/xglfile' + FILEPATH if FILEPATH else ''
                item = dict(
                    oname=XM, anhao=AH, filing_time=LASJStr, trade_name=QY_MC, trade_info=QYXX, uccode=QY_DM,
                    sex=ZXFYMC, age_num=ZXFYDM, content=content, file_url=xq_url, keyword=keyword,
                )
                yield item

            # 列表翻页请求
            totalPage = results[0].get('totalPage')
            cuur_page = response.meta.get('cuur_page', 1)
            if cuur_page < int(totalPage):
                cuur_page += 1
                logger.info(f'开始请求第:{cuur_page}页--搜索词:{keyword}')
                form_data['currentPage'] = str(cuur_page)
                meta_data = {'cuur_page': cuur_page, 'keyword': keyword, 'pCode': pCode, 'captchaId': captchaId, 'form_data': form_data, 'proxy': proxy}
                yield scrapy.FormRequest(url=self.search_url, formdata=form_data, meta=meta_data, priority=3)