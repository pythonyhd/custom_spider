# -*- coding: utf-8 -*-
import json
import random
from json import JSONDecodeError
from urllib.parse import unquote

import jsonpath
import redis
import scrapy
import logging

from custom_spider import settings
from custom_spider.utils.redis_bloomfilter import BloomFilter

logger = logging.getLogger(__name__)


class ShixinCourtSpider(scrapy.Spider):
    name = 'shixin_court'
    allowed_domains = ['zxgk.court.gov.cn']

    custom_settings = {
        'DOWNLOADER_MIDDLEWARES': {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 120,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            'custom_spider.middlewares.RandomProxyMiddlerware': 140,
            'custom_spider.middlewares.LocalRetryMiddlerware': 160,
        },
        "ITEM_PIPELINES": {
            'custom_spider.pipelines.CustomSpiderPipeline': 300,
            'custom_spider.pipelines.MongodbIndexPipeline': 320,
            # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
        },

        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderPriorityQueue",
        "SCHEDULER_PERSIST": True,

        # 大量请求验证码图片出现302
        "HTTPERROR_ALLOWED_CODES": [302],
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        # "DOWNLOAD_DELAY": '1',
    }
    # 列表搜索链接
    search_url = 'http://zxgk.court.gov.cn/shixin/searchSX.do'

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

    def start_requests(self):
        """ 搜索入口 """
        uuid = self.get_uuid()
        img_url = 'http://zxgk.court.gov.cn/shixin/captchaNew.do?captchaId={}&random={}'.format(uuid, random.random())
        # keyword = '北京'
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            yield scrapy.Request(
                url=img_url,
                meta={'uuid': uuid, 'keyword': keyword},
                dont_filter=True,
            )

    def parse(self, response):
        """ 识别验证码 """
        keyword = response.meta.get('keyword')
        uuid = response.meta.get('uuid')
        headers = {'Referer': ''}
        yield scrapy.Request(
            url=settings.CAPTCH_URI,
            method='POST',
            body=response.body,
            headers=headers,
            callback=self.parse_captch,
            meta={'uuid': uuid, 'keyword': keyword},
            dont_filter=True,
        )

    def parse_captch(self, response):
        """ 解析验证码识别结果 """
        keyword = response.meta.get('keyword')
        uuid = response.meta.get('uuid')
        # 解析验证码
        code = json.loads(response.text).get('code')
        # 获取验证码成功开始请求列表页
        if code:
            headers = {"Referer": "http://zxgk.court.gov.cn/xgl/"}
            form_data = {
                "pName": keyword,
                "pCardNum": "",
                "pProvince": "0",
                "pCode": code,
                "captchaId": uuid,
                "currentPage": '1',
            }
            yield scrapy.FormRequest(
                url=self.search_url,
                formdata=form_data,
                headers=headers,
                callback=self.parse_index,
                meta={'keyword': keyword, 'uuid': uuid, 'code': code, 'form_data': form_data},
                priority=3,
            )
        else:
            logger.info('识别验证码失败--没有正确响应')

    def parse_index(self, response):
        """ 解析搜索列表页加翻页请求 """
        keyword = response.meta.get('keyword')
        code = response.meta.get('code')
        uuid = response.meta.get('uuid')
        form_data = response.meta.get('form_data')
        # 放回redis容易造成死循环，一直拿那一个关键词搜索翻页
        if str(response.text) == 'error':
            logger.debug('验证码识别错误或者验证码已经失效--搜索关键词重新保存--重新请求验证码')
            # 用来保存验证码识别错误，或者翻页不能翻到最后一页，验证码就失效的关键词
            self.redis_keyword.sadd(self.name + ':error_keyword', keyword)  # 包含了验证码不能用跟翻页翻不完2种情况的关键词
            uuid = self.get_uuid()
            img_url = 'http://zxgk.court.gov.cn/shixin/captchaNew.do?captchaId={}&random={}'.format(uuid, random.random())
            # 换搜索词
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                return None
            new_keyword = keyword.decode()
            yield scrapy.Request(
                url=img_url,
                meta={'uuid': uuid, 'keyword': new_keyword},
                dont_filter=True,
            )
        else:
            results = json.loads(response.text)
            totalSize = jsonpath.jsonpath(results, expr='$..totalSize')
            if not totalSize:
                return None
            if int(totalSize[0]) == 0:
                logger.info(f"该搜索词没有搜索结果--{keyword}--添加到布隆过滤器")
                if self.bloomfilter_client.is_exist(keyword):
                    logger.info(f"{keyword}--- 没有搜索结果并且被过滤了")
                else:
                    self.bloomfilter_client.add(keyword)
            else:
                # 列表数据解析
                result = results[0].get('result')
                for item in result:
                    id = item.get('id')
                    caseCode = item.get('caseCode')
                    # 详情页
                    url = 'http://zxgk.court.gov.cn/shixin/disDetailNew?id={}&caseCode={}&pCode={}&captchaId={}'.format(id, caseCode, code, uuid)
                    yield scrapy.Request(
                        url=url,
                        callback=self.parse_detail,
                        priority=9,
                    )
                # 列表页翻页请求-如果翻页过多验证码会失效
                total_page = results[0].get('totalPage')  # 没有搜索结果跟只有一页都显示1
                cuur_page = response.meta.get('cuur_page', 1)
                if cuur_page < int(total_page):
                    cuur_page += 1
                    logger.info(f'请求第:{cuur_page}页--搜索词:{keyword}')
                    form_data['currentPage'] = str(cuur_page)
                    yield scrapy.FormRequest(
                        url=self.search_url,
                        formdata=form_data,
                        callback=self.parse_index,
                        meta={'cuur_page': cuur_page, 'keyword': keyword, 'form_data': form_data, 'code': code, 'uuid': uuid},
                        priority=7,
                    )

    def parse_detail(self, response):
        """
        详情页解析
        :param response:
        :return:
        """
        try:
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

            # id = item.get('id')  # 标识
            partyTypeName = item.get('partyTypeName')
            # performedPart = item.get('performedPart')  # 不知道含义
            # qysler = item.get('qysler')  # 不知道含义
            court_item = dict(
                oname=iname, pname=businessEntity, sf=areaName, dqmc=areaName, uccode=cardNum, bzxr_xb=sexy, age=age,
                zxfy=courtName, zxwh=gistId, anhao=caseCode, cf_wsh=caseCode, cf_xzjg=gistUnit, lian_sj=regDate,
                cf_jdrq=regDate, yiwu=duty, lvxingqk=performance, qingxing=disruptTypeName, fb_rq=publishDate,
                xq_url=unquote(response.url), zx_bd=unperformPart, ws_nr_txt=json.dumps(item, ensure_ascii=False),
                bz=partyTypeName,
            )
            # print(court_item)
            yield court_item
        except JSONDecodeError:
            logger.error(f'详情页无法解析--不是json数据:{response.text}')

    def get_uuid(self):
        """ 获取验证码uuid参数 """
        chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A',
                 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
                 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k',
                 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
                 'x', 'y', 'z']
        uuid = ''
        for i in range(32):
            _idx = int(random.random() * 61)
            uuid += chars[_idx]
        return uuid
