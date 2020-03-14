# -*- coding: utf-8 -*-
'''
import json
import random
from io import BytesIO

import scrapy
import logging
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox

from custom_spider import settings

logger = logging.getLogger(__name__)


class ParseCaptchaSpider(scrapy.Spider):
    name = 'parse_captcha'
    allowed_domains = ['zxgk.court.gov.cn']

    def start_requests(self):
        """ 关键词搜索函数，换一个搜索词换一张图片，请求验证码图片 """
        keywords = ['北京', '张婧']
        for keyword in keywords:
            uuid = self.process_uuid()
            captcha_url = 'http://zxgk.court.gov.cn/shixin/captchaNew.do?captchaId={}&random={}'.format(uuid, random.random())
            meta_data = {'uuid': uuid, 'keyword': keyword}
            yield scrapy.Request(url=captcha_url, meta=meta_data)

    def parse(self, response):
        """ 解析验证码图片 """
        keyword = response.meta.get('keyword')
        uuid = response.meta.get('uuid')
        # 请求本地验证码识别接口
        yield scrapy.Request(
            url=settings.CAPTCH_URI,
            method='POST',
            body=response.body,
            callback=self.parse_captcha,
            meta={'uuid': uuid, 'keyword': keyword, 'proxy': None},
            dont_filter=True,
        )

    def parse_captcha(self, response):
        """ 获取验证码识别结果，请求列表第一页 """
        # 解析验证码
        code = json.loads(response.text).get('code')
        # 获取验证码成功--开始请求列表页第一页

    @classmethod
    def process_uuid(cls):
        """ 获取唯一参数 """
        chars = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A',
                 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y',
                 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k',
                 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w',
                 'x', 'y', 'z']
        uuid = ''
        for _ in range(32):
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
'''