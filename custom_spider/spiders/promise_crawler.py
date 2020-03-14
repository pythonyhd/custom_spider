# -*- coding: utf-8 -*-
import json
import logging
from urllib.parse import unquote

import jsonpath
import redis
import scrapy

from custom_spider import settings
from custom_spider.config import shixin_custom_settings
from custom_spider.utils.bloomfilter import BloomFilter
from custom_spider.work_utils.process_captcha import CaptchaProcess

logger = logging.getLogger(__name__)


class PromiseCrawlerSpider(scrapy.Spider):
    name = 'promise_crawler'
    allowed_domains = ['zxgk.court.gov.cn']
    cap = CaptchaProcess()
    search_url = 'http://zxgk.court.gov.cn/shixin/searchSX.do'  # 失信被执行人搜索列表页url

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

    custom_settings = shixin_custom_settings

    def start_requests(self):
        """ 关键词搜索函数，换一个搜索词换一张图片，请求验证码图片 """
        # keywords = ['马俊华', '张倩', '张婧']
        # for keyword in keywords:
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            captcha_item = self.cap.main()
            pCode = captcha_item.get("code")
            captchaId = captcha_item.get('captchaId')
            form_data = {
                "pName": keyword,
                "pCardNum": "",
                "pProvince": "0",
                "pCode": str(pCode),
                "captchaId": str(captchaId),
                "currentPage": '1',
            }
            yield scrapy.FormRequest(
                url=self.search_url,
                formdata=form_data,
                callback=self.parse_index,
                meta={'keyword': keyword, 'captchaId': captchaId, 'pCode': pCode, 'form_data': form_data},
            )

    def parse_index(self, response):
        """ 解析列表第一页，列表页翻页 """
        keyword = response.meta.get('keyword')
        pCode = response.meta.get('pCode')
        captchaId = response.meta.get('captchaId')
        form_data = response.meta.get('form_data')
        # 列表解析
        results = json.loads(response.text)
        totalSize = jsonpath.jsonpath(results, expr='$..totalSize')
        # 把没有搜索结果的搜索词添加到布隆过滤器进行过滤，避免多次搜索同样的词，放再程序开头如果有搜索结果，就没法更新最新数据了
        if int(totalSize[0]) == 0:
            if self.bloomfilter_client.is_exist(keyword):
                logger.info(f"{keyword}--- 没有搜索结果并且被过滤了")
            else:
                logger.debug(f"该搜索词没有搜索结果--{keyword}--添加到布隆过滤器")
                self.bloomfilter_client.add(keyword)
        else:
            result = results[0].get('result')
            for item in result:
                id = item.get('id')
                caseCode = item.get('caseCode')
                # 详情页
                url = 'http://zxgk.court.gov.cn/shixin/disDetailNew?id={}&caseCode={}&pCode={}&captchaId={}'.format(id, caseCode, pCode, captchaId)
                yield scrapy.Request(url=url, meta={'keyword': keyword}, callback=self.parse_detail, priority=9)

            total_page = results[0].get('totalPage')  # 没有搜索结果跟只有一页都显示1
            # # for循环翻页--容易造成请求队列堆积之后验证码失效
            # is_first = response.meta.get('is_first', True)
            # if is_first and total_page > 1:
            #     for page in range(2, int(total_page) + 1):
            #         form_data['currentPage'] = str(page)
            #         meta_data = {'is_first': False, 'keyword': keyword, 'form_data': form_data, 'pCode': pCode, 'captchaId': captchaId}
            #         yield scrapy.FormRequest(
            #             url=self.search_url,
            #             formdata=form_data,
            #             callback=self.parse_index,
            #             meta=meta_data,
            #             priority=7,
            #         )

            # 列表页翻页请求--一页一页的进行翻页
            cuur_page = response.meta.get('cuur_page', 1)
            if cuur_page < int(total_page):
                cuur_page += 1
                logger.info(f'请求第:{cuur_page}页--搜索词:{keyword}')
                form_data['currentPage'] = str(cuur_page)
                yield scrapy.FormRequest(
                    url=self.search_url,
                    formdata=form_data,
                    callback=self.parse_index,
                    meta={'cuur_page': cuur_page, 'keyword': keyword, 'form_data': form_data, 'pCode': pCode, 'captchaId': captchaId},
                    priority=7,
                )

    def parse_detail(self, response):
        """ 解析详情页 """
        keyword = response.meta.get('keyword')  # 存储keyword去数据库对比，关键词抓取条数跟网站是否一致
        # 详情解析
        item = json.loads(response.text)
        iname = item.get('iname', '')  # 被执行人姓名/名称
        caseCode = item.get('caseCode', '')  # 案号
        age = item.get('age', '')  # 年龄
        sexy = item.get('sexy', '')  # 性别
        cardNum = item.get('cardNum', '')  # 身份证号或者统一社会信用代码
        courtName = item.get('courtName', '')  # 执行法院
        areaName = item.get('areaName', '')  # 省份
        gistId = item.get('gistId', '')  # 执行依据文号
        regDate = item.get('regDate', '')  # 立案时间
        gistUnit = item.get('gistUnit', '')  # 做出执行依据单位
        duty = item.get('duty', '')  # 生效法律文书确定的义务
        performance = item.get('performance', '')  # 被执行人的履行情况
        disruptTypeName = item.get('disruptTypeName', '')  # 失信被执行人行为具体情形
        publishDate = item.get('publishDate', '')  # 发布时间
        businessEntity = item.get('businessEntity', '')  # 法人
        unperformPart = item.get('unperformPart', '')  # 执行标的
        partyTypeName = item.get('partyTypeName', '')

        court_item = dict(
            oname=iname, pname=businessEntity, sf=areaName, dqmc=areaName, uccode=cardNum, bzxr_xb=sexy, age=age,
            zxfy=courtName, zxwh=gistId, anhao=caseCode, cf_wsh=caseCode, cf_xzjg=gistUnit, lian_sj=regDate,
            cf_jdrq=regDate, yiwu=duty, lvxingqk=performance, qingxing=disruptTypeName, fb_rq=publishDate,
            xq_url=unquote(response.url), zx_bd=unperformPart, ws_nr_txt=json.dumps(item, ensure_ascii=False),
            bz=partyTypeName, keyword=keyword
        )
        yield court_item