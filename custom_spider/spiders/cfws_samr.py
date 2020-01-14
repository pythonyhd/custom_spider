# -*- coding: utf-8 -*-
import base64
import json
import os

import execjs
import jsonpath
import scrapy
import logging

logger = logging.getLogger(__name__)


class CfwsSamrSpider(scrapy.Spider):
    name = 'cfws_samr'
    allowed_domains = ['cfws.samr.gov.cn']

    custom_settings = {
        "DOWNLOADER_MIDDLEWARES": {
            'custom_spider.middlewares.RandomUserAgentMiddleware': 120,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,  # 禁用默认的代理
            'custom_spider.middlewares.RandomProxyMiddlerware': 140,
            # 'custom_spider.middlewares.LocalRetryMiddlerware': 160,
        },
        # "ITEM_PIPELINES": {
            # 'custom_spider.pipelines.CustomPipeline': 300,
            # 'custom_spider.pipelines.MongodbIndexPipeline': 320,
            # 'custom_spider.pipelines.MysqlTwistedPipeline': 340,
        # },
        "REDIRECT_ENABLED": False,
        "RETRY_ENABLED": True,
        "RETRY_TIMES": '9',
        "DOWNLOAD_TIMEOUT": '25',
        # "DOWNLOAD_DELAY": '0.05',
    }
    search_url = 'http://cfws.samr.gov.cn/queryDoc'  # 列表搜索链接
    index_url = 'http://cfws.samr.gov.cn/getDoc'  # 详情页url
    ciphertext_path = os.path.dirname(os.path.dirname(__file__)) + r'/templates/samr_js.js'
    file_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) + r'/files/'

    def start_requests(self):
        """ 列表搜索入口 """
        ciphertext = self.run_sourse_js()
        form_data = {
            "pageSize": "5",
            "pageNum": "1",
            "queryCondition": '[]',  # 搜素条件，需要添加各种条件
            "sortFields": "23_s:asc,16_s:asc",
            "ciphertext": str(ciphertext),
        }
        yield scrapy.FormRequest(
            url=self.search_url,
            formdata=form_data,
            meta={'form_data': form_data},
        )

    def parse(self, response):
        """ 列表页解析翻页 """
        results = json.loads(response.text)
        # 解析
        resultList = results.get('result').get('queryResult').get('resultList')
        if not resultList:
            return None
        for result in resultList:
            cf_wsh = result.get('2')  # 文书号
            cf_content = result.get('7')  # 处罚内容
            cf_xzjg = result.get('14')  # 处罚机关
            cf_jdrq = result.get('23')  # 处罚日期
            oname = result.get('30')  # 当事人名称
            ws_nr_txt= json.dumps(result, ensure_ascii=False)

            rowkey = result.get('rowkey')  # PDF详情
            base_item = dict(
                oname=oname,
                cf_wsh=cf_wsh,
                cf_xzjg=cf_xzjg,
                cf_content=cf_content,
                cf_jdrq=cf_jdrq,
                ws_nr_txt=ws_nr_txt,
            )
            ciphertext = self.run_sourse_js()
            form_data = {
                'ciphertext': str(ciphertext),
                'docid': str(rowkey),
            }
            yield scrapy.FormRequest(
                url=self.index_url,
                formdata=form_data,
                callback=self.parse_details,
                meta={'base_item': base_item},
                priority=7,
            )

        # 列表翻页请求
        form_data = response.meta.get('form_data')
        is_first = response.meta.get('is_first', True)
        resultCount = jsonpath.jsonpath(results, expr=r'$..result.queryResult.resultCount')
        if is_first:
            if resultCount:
                total_page = int(int(resultCount[0]) / 5) if int(resultCount[0]) % 5 == 0 else int(int(resultCount[0]) / 5) + 1
                total_page = 10 if total_page > 10 else total_page  # 最多翻10页，只能通过添加各种条件遍历
                for page in range(2, total_page + 1):
                    ciphertext = self.run_sourse_js()
                    form_data['pageNum'] = str(page)
                    form_data['ciphertext'] = str(ciphertext)
                    yield scrapy.FormRequest(
                        url=self.search_url,
                        formdata=form_data,
                        meta={'is_first': False, 'form_data': form_data},
                        priority=3,
                    )
            else:
                logger.info(f'获取总页数失败--{results}')

    def parse_details(self, response):
        """ 详情页解析 """
        results = json.loads(response.text)
        result = results.get('result')
        cf_wsh = result.get('i0')  # 文书号
        cf_jdrq = result.get('i1')  # 处罚日期
        cf_xzjg = result.get('i3')  # 处罚机关
        cf_cflb = result.get('i4')  # 处罚种类
        cf_yj = result.get('i5')  # 处罚依据
        content = result.get('i7')  # pdf文件内容
        files = self.get_pdf(cf_wsh, content)
        print(cf_wsh)

    def run_sourse_js(self):
        """ 执行JS获取参数 """
        with open(self.ciphertext_path, 'r', encoding='utf-8') as f:
            js_parttern = execjs.compile(f.read())
            result = js_parttern.call('cipher')
            return result

    def get_pdf(self, filename: str, string: str):
        """ 存储PDF文件 """
        content = base64.b64decode(string)
        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)
        with open(self.file_path + filename + r'.pdf', 'wb') as file:
            file.write(content)