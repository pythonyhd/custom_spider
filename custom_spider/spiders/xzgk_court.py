# -*- coding: utf-8 -*-
import json
import random
import re
from functools import reduce
from io import BytesIO

import jsonpath
import redis
import scrapy
import logging
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox

from custom_spider import settings
from custom_spider.utils.redis_bloomfilter import BloomFilter

logger = logging.getLogger(__name__)


class XzgkCourtSpider(scrapy.Spider):
    name = 'xzgk_court'
    allowed_domains = ['zxgk.court.gov.cn']
    start_urls = ['http://zxgk.court.gov.cn/']

    custom_settings = {
        'DEFAULT_REQUEST_HEADERS': {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "zxgk.court.gov.cn",
            "Origin": "http://zxgk.court.gov.cn",
            "X-Requested-With": "XMLHttpRequest",
        },
        'DOWNLOADER_MIDDLEWARES': {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 120,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            # 'custom_spider.middlewares.CloudProxyMiddleware': 140,  # 代理必须从头到尾是一个
            # 'custom_spider.middlewares.LocalRetryMiddlerware': 160,
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

        # 大量请求验证码图片出现302，请求解析PDF也会出现302
        "HTTPERROR_ALLOWED_CODES": [302],
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        "DOWNLOAD_DELAY": '1',
    }

    search_url = 'http://zxgk.court.gov.cn/xgl/searchXgl.do'  # 搜索链接
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

    # redis 代理池
    redis_proxy = redis.StrictRedis(
        host=settings.REDIS_PROXIES_HOST,
        port=settings.REDIS_PROXIES_PORT,
        password=settings.REDIS_PROXIES_PASSWORD,
        db=settings.REDIS_PROXIES_DB,
    )

    def start_requests(self):
        """ 搜索入口 """
        uuid = self.get_uuid()
        img_url = 'http://zxgk.court.gov.cn/xgl/captchaXgl.do?captchaId={}&random={}'.format(uuid, random.random())
        while True:
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                break
            keyword = keyword.decode()
            proxy = self.get_random_ip(img_url)
            logger.info(f'当前代理:{proxy}--搜索词:{keyword}')
            yield scrapy.Request(
                url=img_url,
                meta={'uuid': uuid, 'keyword': keyword, 'proxy': proxy},
                dont_filter=True,
            )

    def parse(self, response):
        """ 识别验证码 """
        keyword = response.meta.get('keyword')
        uuid = response.meta.get('uuid')
        proxy = response.meta.get('proxy')
        headers = {'Referer': ''}
        yield scrapy.Request(
            url=settings.CAPTCH_URI,
            method='POST',
            body=response.body,
            headers=headers,
            callback=self.parse_captch,
            meta={'uuid': uuid, 'keyword': keyword, 'proxy_ip': proxy},
            dont_filter=True,
        )

    def parse_captch(self, response):
        """ 解析验证码识别结果 """
        keyword = response.meta.get('keyword')
        uuid = response.meta.get('uuid')
        proxy_ip = response.meta.get('proxy_ip')
        # 解析验证码
        code = json.loads(response.text).get('code')
        # 获取验证码成功--开始请求列表页第一页--第一页不生成dupefilter--用来更新
        if code:
            headers = {"Referer": "http://zxgk.court.gov.cn/xgl/"}
            form_data = {
                'pName': str(keyword),
                'pCardNum': '',
                'selectCourtId': '0',
                'pCode': str(code),  # 验证码识别结果
                'captchaId': str(uuid),  # 验证码唯一标识
                'searchCourtName': '全国法院（包含地方各级法院）',
                'selectCourtArrange': '1',
                'currentPage': '1',  # 翻页参数
            }
            yield scrapy.FormRequest(
                url=self.search_url,
                formdata=form_data,
                headers=headers,
                callback=self.parse_index,
                meta={'keyword': keyword, 'uuid': uuid, 'code': code, 'form_data': form_data, 'proxy': proxy_ip},
                dont_filter=True,
                priority=3,
            )
        else:
            logger.info('识别验证码失败--没有正确响应')

    def parse_index(self, response):
        """ 解析搜索列表页加翻页请求 """
        keyword = response.meta.get('keyword')
        form_data = response.meta.get('form_data')
        proxy = response.meta.get('proxy')
        # 验证码识别错误--更换新IP--更换验证码--更换搜索关键词(失败的词重新放回redis)
        if str(response.text) == 'error验证码校验失败，重新刷验证码':
            logger.info('验证码识别错误或者翻页过多导致失效问题--搜索关键词放回redis--重新请求验证码')
            self.redis_keyword.sadd(self.name + ':error_keyword', keyword)
            uuid = self.get_uuid()
            img_url = 'http://zxgk.court.gov.cn/xgl/captchaXgl.do?captchaId={}&random={}'.format(uuid, random.random())
            # 更换搜索关键词
            keyword = self.redis_keyword.rpop(self.reids_name)
            if not keyword:
                return None
            new_keyword = keyword.decode()
            # 更换新IP
            new_proxy = self.get_random_ip(img_url)
            yield scrapy.Request(
                url=img_url,
                meta={'uuid': uuid, 'keyword': new_keyword, 'proxy': new_proxy},
                dont_filter=True,
            )
        else:
            results = json.loads(response.text)
            totalSize = jsonpath.jsonpath(results, expr='$..totalSize')
            if not totalSize:
                return None
            if int(totalSize[0]) == 0:
                if self.bloomfilter_client.is_exist(keyword):
                    logger.info(f"{keyword}--- 被过滤了")
                else:
                    logger.info(f"该搜索词没有搜索结果--{keyword}--添加到布隆过滤器")
                    self.bloomfilter_client.add(keyword)

            else:
                # 解析
                result_list = results[0].get('result')  # 成功之后进行解析
                for result in result_list:
                    AH = result.get('AH')  # 案号
                    LASJStr = result.get('LASJStr')  # 立案时间
                    XM = result.get('XM')  # 姓名主体
                    QYXX = result.get('QYXX')  # 企业信息
                    QY_MC = result.get('QY_MC')  # 企业名称
                    QY_DM = result.get('QY_DM')  # 企业代码
                    ZXFYMC = result.get('ZXFYMC')  # 性别
                    bz = result.get('jsonObject')  # 数据字典
                    ws_nr_txt = json.dumps(result, ensure_ascii=False)
                    FILEPATH = result.get('FILEPATH')  # PDF文件链接
                    xq_url = 'http://zxgk.court.gov.cn/xglfile' + FILEPATH
                    item = dict(
                        oname=XM,
                        anhao=AH,
                        cf_wsh=AH,
                        lian_sj=LASJStr,
                        ztmc_lx=QY_MC,
                        cf_cfmc=QYXX,
                        uccode=QY_DM,
                        bzxr_xb=ZXFYMC,
                        bz=bz,
                        ws_nr_txt=ws_nr_txt,
                        xq_url=xq_url,
                    )
                    if FILEPATH:
                        yield scrapy.Request(
                            url=xq_url,
                            callback=self.parse_xzgxf_pdf,
                            meta={'item': item},
                            priority=5,
                        )
                    else:
                        yield item

                # 翻页请求
                headers = {"Referer": "http://zxgk.court.gov.cn/xgl/"}
                totalpage = results[0].get('totalPage')  # 总页数
                cuur_page = response.meta.get('cuur_page', 1)
                if cuur_page < int(totalpage):
                    cuur_page += 1
                    logger.info(f'请求第:{cuur_page}页--搜索词:{keyword}')
                    form_data['currentPage'] = str(cuur_page)
                    yield scrapy.FormRequest(
                        url=self.search_url,
                        formdata=form_data,
                        headers=headers,
                        callback=self.parse_index,
                        meta={'cuur_page': cuur_page, 'keyword': keyword, 'form_data': form_data, 'proxy': proxy},
                        priority=7,
                    )

    def parse_xzgxf_pdf(self, response):
        """ 解析-限制高消费-PDF文件 """
        item = response.meta.get('item')
        # 解析PDF详情
        try:
            content_list = self.parse_pdf(response)
            item['cf_jdrq'] = self.handles_cf_jdrq(content_list[-1]) if content_list else None
            re_com = re.compile(r'\r|\n|\t|\s')
            content = reduce(lambda x, y: x + y, [re_com.sub('', i) for i in content_list]).replace('(cid:9)', '')
            item['content'] = content
            cf_sy_pattern = re.compile(r'本院于.*?给付义务')
            cf_yj_pattern = re.compile(r'本院依照.*?采取限制消费措施')
            cf_sy = cf_sy_pattern.search(content)
            if cf_sy:
                item['cf_sy'] = cf_sy.group()
            else:
                item['cf_sy'] = ''
            cf_yj = cf_yj_pattern.search(content)
            if cf_yj:
                item['cf_yj'] = cf_yj.group()
            else:
                item['cf_yj'] = ''
            # print(item)
            yield item
        except Exception as e:
            logger.error(f"PDF解析出错--直接返回item:{repr(e)}")
            content_list = []
            yield item

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

    def parse_pdf(self, response):
        """ 解析PDF文件 """
        # 用文件对象来创建一个pdf文档分析器
        praser = PDFParser(BytesIO(response.body))
        # 创建一个PDF文档
        doc = PDFDocument()
        # 连接分析器 与文档对象
        praser.set_document(doc)
        doc.set_parser(praser)
        # 提供初始化密码
        # 如果没有密码 就创建一个空的字符串
        doc.initialize()
        # 检测文档是否提供txt转换，不提供就忽略
        if not doc.is_extractable:
            raise PDFTextExtractionNotAllowed
        else:
            # 创建PDf 资源管理器 来管理共享资源
            rsrcmgr = PDFResourceManager()
            # 创建一个PDF设备对象
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            # 创建一个PDF解释器对象
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            contents_list = []
            # 循环遍历列表，每次处理一个page的内容
            for page in doc.get_pages():  # doc.get_pages() 获取page列表
                # 接受该页面的LTPage对象
                interpreter.process_page(page)
                # 这里layout是一个LTPage对象 里面存放着
                # 这个page解析出的各种对象 一般包括LTTextBox, LTFigure, LTImage, LTTextBoxHorizontal 等等
                # 想要获取文本就获得对象的text属性
                layout = device.get_result()
                for index, out in enumerate(layout):
                    if isinstance(out, LTTextBox):
                        contents = out.get_text().strip()
                        contents_list.append(contents)
            return contents_list

    def handles_cf_jdrq(self, cf_jdrq):
        """ 汉字的日期转数字日期 """
        mapper = {"〇": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8",
                  "九": "9", "年": "-", "月": "-", "日": "-"}

        # 替换年月日，及1-9汉字
        new_jdrq = ""
        for word in cf_jdrq:
            if word in mapper.keys():
                new_jdrq += mapper[word]
            else:
                new_jdrq += word

        # 处理十，分几种情况，1.在最左边，在中间，在最后边
        cf_jdrq = ""
        digit_list = [str(digit) for digit in range(1, 10)]
        for idx, word in enumerate(new_jdrq):
            if word == "十":
                # 最左边
                if new_jdrq[idx - 1] == '-' and new_jdrq[idx + 1] in digit_list:
                    cf_jdrq += "1"
                elif new_jdrq[idx - 1] == "-" and new_jdrq[idx + 1] not in digit_list:
                    cf_jdrq += "10"
                elif new_jdrq[idx - 1] in digit_list and new_jdrq[idx + 1] in digit_list:
                    cf_jdrq += ""
                else:
                    cf_jdrq += "0"
            else:
                cf_jdrq += word
        return cf_jdrq[:-1]

    def get_random_ip(self, url):
        """ 获取随机代理 """

        ip_port = self.redis_proxy.srandmember('proxies')
        proxies = {
            'http': 'http://{}'.format(ip_port.decode('utf-8')),
            'https': 'https://{}'.format(ip_port.decode('utf-8')),
        }
        if url.startswith('http'):
            return proxies.get('http')
        else:
            return proxies.get('https')

