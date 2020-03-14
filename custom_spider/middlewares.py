# -*- coding: utf-8 -*-
import base64
import json
import re
import time
from json import JSONDecodeError
from urllib.parse import unquote, parse_qsl, urlencode

import redis
from fake_useragent import UserAgent
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.python import global_object_name
from scrapy.utils.response import response_status_message
import logging

from custom_spider import settings
from custom_spider.work_utils.process_captcha import CaptchaProcess, ExecuteCaptchaProcess, ConsumptionCaptchaProcess

logger = logging.getLogger(__name__)


class RandomUserAgentMiddleware(object):
    """ 利用fake_useragent生成随机请求头 """
    def __init__(self, ua_type):
        self.ua_type = ua_type
        self.ua = UserAgent()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            ua_type=crawler.settings.get('RANDOM_UA_TYPE', 'random')
        )

    def process_request(self, request, spider):
        def get_user_agent():
            return getattr(self.ua, self.ua_type)
        request.headers.setdefault(b'User-Agent', get_user_agent())


class RandomProxyMiddlerware(object):
    """ 拨号代理池，set类型，无账号密码 """
    def __init__(self, proxy_redis_host, proxy_redis_port, proxy_redis_password, proxy_redis_db):
        self.redis_proxy = redis.StrictRedis(host=proxy_redis_host, port=proxy_redis_port, password=proxy_redis_password, db=proxy_redis_db)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            proxy_redis_host=crawler.settings.get('REDIS_PROXIES_HOST'),
            proxy_redis_port=crawler.settings.get('REDIS_PROXIES_PORT'),
            proxy_redis_password=crawler.settings.get('REDIS_PROXIES_PASSWORD'),
            proxy_redis_db=crawler.settings.get('REDIS_PROXIES_DB'),
        )

    def process_request(self, request, spider):
        ip_port = self.redis_proxy.srandmember('proxies')
        if ip_port:
            proxies = {
                'http': 'http://{}'.format(ip_port.decode('utf-8')),
                'https': 'https://{}'.format(ip_port.decode('utf-8')),
            }
            if request.url.startswith('http://'):
                request.meta['proxy'] = proxies.get("http")
                logger.debug('http链接,ip:{}'.format(request.meta.get('proxy')))
            else:
                request.meta['proxy'] = proxies.get('https')
                logger.debug('https链接,ip:{}'.format(request.meta.get('proxy')))
        else:
            logger.info('代理池枯竭--IP数量不足--等待重新拨号')
            time.sleep(10)


class CloudProxyMiddleware(object):
    """ 百度云服务器-私有账号密码IP """
    def process_request(self, request, spider):
        proxy = {'ip_port': '106.12.35.126:443', 'user_pass': 'kinglife:fy1812!!'}
        if request.url.startswith('http://'):
            request.meta['proxy'] = "http://{}".format(proxy.get('ip_port'))
            encoded_user_pass = base64.b64encode(proxy.get('user_pass').encode('utf-8'))
            request.headers['Proxy-Authorization'] = 'Basic ' + encoded_user_pass.decode()
            logger.debug('http链接,ip:{}'.format(request.meta.get('proxy')))
        else:
            request.meta['proxy'] = "https://{}".format(proxy.get('ip_port'))
            encoded_user_pass = base64.b64encode(proxy.get('user_pass').encode('utf-8'))
            request.headers['Proxy-Authorization'] = 'Basic ' + encoded_user_pass.decode()
            logger.debug('https链接,ip:{}'.format(request.meta.get('proxy')))


class CheckResponseMiddleware(object):
    """ 失信被执行人响应检查，请求参数修改中间件，处理验证码失效无法翻页问题 """
    cap = CaptchaProcess()

    def process_response(self, request, response, spider):
        # 处理列表页
        if 'searchSX' in response.url:
            if str(response.text) == 'error':
                # 修改请求参数当中的验证码标识跟验证码识别结果，重新更换了一张新的验证码图片
                captcha_item = self.cap.main()
                code = captcha_item.get("code")
                captchaId = captcha_item.get('captchaId')
                logger.info('列表页验证码失效--开始更换新的验证码--重新请求')
                # 获取旧的已经失效的列表请求参数
                request_body = unquote(request.body.decode())
                request_dict = dict(parse_qsl(request_body))
                # 修改列表失效的请求参数-POST请求--修改验证码跟对应的captchaId
                request_dict['pCode'] = code
                request_dict['captchaId'] = captchaId
                quote_body = urlencode(request_dict)
                # 修改form_data里面得参数，需要更换成新的
                form_data = request.meta.get('form_data')
                form_data['pCode'] = code
                form_data['captchaId'] = captchaId
                # 修改meta传递的参数信息为新的信息
                request.meta['pCode'] = code
                request.meta['captchaId'] = captchaId
                request = request.replace(body=quote_body, meta=request.meta)
                request.priority = 10
                return request

        # 处理详情页
        if 'disDetailNew' in response.url:
            if str(response.text) == '{}':
                captcha_item = self.cap.main()
                code = captcha_item.get("code")
                captchaId = captcha_item.get('captchaId')
                logger.info(f'详情页验证码失效--更换验证码--重新请求--识别结果:{code}')
                # 替换详情url中的验证码跟唯一标识--GET请求
                url = re.sub(r'pCode=(.*?)&', 'pCode={}&', response.url)
                url = re.sub(r'captchaId=(.+)', 'captchaId={}', url)
                link = url.format(code, captchaId)
                request = request.replace(url=link)
                return request

        return response


class CheckEcecuteMiddleware(object):
    """被执行人,响应检查，请求参数修改中间件，处理验证码失效无法翻页问题"""
    exe_cap = ExecuteCaptchaProcess()

    def process_response(self, request, response, spider):
        # 处理列表页
        if 'searchBzxr' in response.url:
            if response.status != 200:
                captcha_item = self.exe_cap.main()
                code = captcha_item.get("code")
                captchaId = captcha_item.get('captchaId')
                logger.info('列表页验证码失效--开始更换新的验证码--重新请求')
                # 获取旧的已经失效的列表请求参数
                request_body = unquote(request.body.decode())
                request_dict = dict(parse_qsl(request_body))
                # 修改列表失效的请求参数-POST请求--修改验证码跟对应的captchaId
                request_dict['pCode'] = code
                request_dict['captchaId'] = captchaId
                quote_body = urlencode(request_dict)
                # 修改form_data里面得参数，需要更换成新的
                form_data = request.meta.get('form_data')
                form_data['pCode'] = code
                form_data['captchaId'] = captchaId
                # 修改meta传递的参数信息为新的信息
                request.meta['pCode'] = code
                request.meta['captchaId'] = captchaId
                request = request.replace(body=quote_body, meta=request.meta)
                request.priority = 10
                return request
            else:
                try:
                    json.loads(response.text)
                    return response
                except JSONDecodeError:
                    captcha_item = self.exe_cap.main()
                    code = captcha_item.get("code")
                    captchaId = captcha_item.get('captchaId')
                    logger.info('列表页验证码失效--开始更换新的验证码--重新请求')
                    # 获取旧的已经失效的列表请求参数
                    request_body = unquote(request.body.decode())
                    request_dict = dict(parse_qsl(request_body))
                    # 修改列表失效的请求参数-POST请求--修改验证码跟对应的captchaId
                    request_dict['pCode'] = code
                    request_dict['captchaId'] = captchaId
                    quote_body = urlencode(request_dict)
                    # 修改form_data里面得参数，需要更换成新的
                    form_data = request.meta.get('form_data')
                    form_data['pCode'] = code
                    form_data['captchaId'] = captchaId
                    # 修改meta传递的参数信息为新的信息
                    request.meta['pCode'] = code
                    request.meta['captchaId'] = captchaId
                    request = request.replace(body=quote_body, meta=request.meta)
                    request.priority = 10
                    return request
        # 处理详情页
        if 'newdetail' in response.url:
            if str(response.text) == '{}':
                captcha_item = self.exe_cap.main()
                code = captcha_item.get("code")
                captchaId = captcha_item.get('captchaId')
                logger.info(f'详情页验证码失效--更换验证码--重新请求--识别结果:{code}')
                # 替换详情url中的验证码跟唯一标识--GET请求
                url = re.sub(r'pCode=(.*?)&', 'pCode={}&', response.url)
                url = re.sub(r'captchaId=(.+)', 'captchaId={}', url)
                link = url.format(code, captchaId)
                request = request.replace(url=link)
                return request

        return response


class ChechConsumMiddleware(object):
    """限制高消费响应结果检查"""
    cap = ConsumptionCaptchaProcess()

    def process_response(self, request, response, spider):
        if 'searchXgl' in response.url:
            if response.status != 200:
                captcha_item = self.cap.main()
                pCode = captcha_item.get("code")
                captchaId = captcha_item.get('captchaId')
                proxy = captcha_item.get('proxy').get('http')
                logger.info(f'列表页验证码失效--开始更换新的验证码--重新请求--新验证码识别结果:{pCode}--新IP:{proxy}')
                # 获取旧的已经失效的列表请求参数
                request_body = unquote(request.body.decode())
                request_dict = dict(parse_qsl(request_body))
                # 修改列表失效的请求参数-POST请求--修改验证码跟对应的captchaId
                request_dict['pCode'] = pCode
                request_dict['captchaId'] = captchaId
                request_dict['pCardNum'] = ""  # 该参数绝对不能缺失，否则造成翻页不成功
                quote_body = urlencode(request_dict)
                # 修改form_data里面得参数，需要更换成新的
                form_data = request.meta.get('form_data')
                form_data['pCode'] = pCode
                form_data['captchaId'] = captchaId
                # 修改meta传递的参数信息为新的信息
                request.meta['pCode'] = pCode
                request.meta['captchaId'] = captchaId
                request.meta['proxy'] = proxy
                request = request.replace(body=quote_body, meta=request.meta)
                request.priority = 10
                return request
            else:
                try:
                    json.loads(response.text)
                    return response
                except JSONDecodeError:
                    captcha_item = self.cap.main()
                    pCode = captcha_item.get("code")
                    captchaId = captcha_item.get('captchaId')
                    proxy = captcha_item.get('proxy').get('http')
                    logger.info(f'列表页验证码失效--开始更换新的验证码--重新请求--新验证码识别结果:{pCode}--新IP:{proxy}')
                    # 获取旧的已经失效的列表请求参数
                    request_body = unquote(request.body.decode())
                    request_dict = dict(parse_qsl(request_body))
                    # 修改列表失效的请求参数-POST请求--修改验证码跟对应的captchaId
                    request_dict['pCode'] = pCode
                    request_dict['captchaId'] = captchaId
                    request_dict['pCardNum'] = ""
                    quote_body = urlencode(request_dict)
                    # 修改form_data里面得参数，需要更换成新的
                    form_data = request.meta.get('form_data')
                    form_data['pCode'] = pCode
                    form_data['captchaId'] = captchaId
                    # 修改meta传递的参数信息为新的信息
                    request.meta['pCode'] = pCode
                    request.meta['captchaId'] = captchaId
                    request.meta['proxy'] = proxy
                    request = request.replace(body=quote_body, meta=request.meta)
                    request.priority = 10
                    return request

        return response

    def process_exception(self, request, exception, spider):
        if 'ConnectionRefusedError' in repr(exception) or 'TimeoutError' in repr(exception) or 'TCPTimedOutError' in repr(exception):
            captcha_item = self.cap.main()
            pCode = captcha_item.get("code")
            captchaId = captcha_item.get('captchaId')
            proxy = captcha_item.get('proxy').get('http')
            logger.info(f'进入异常请求--新验证码识别结果:{pCode}--新IP:{proxy}')
            # 修改列表请求参数-POST请求
            request_body = unquote(request.body.decode())
            request_dict = dict(parse_qsl(request_body))
            print(f'旧的请求参数:{request_dict}--旧的meta信息:{request.meta}')
            # 修改列表页POST请求参数
            request_dict['pCode'] = pCode
            request_dict['captchaId'] = captchaId
            request_dict['pCardNum'] = ""
            quote_body = urlencode(request_dict)
            # 修改request.meta里面得参数，form_data里面得参数也需要更换成新的
            form_data = request.meta.get('form_data')
            form_data['pCode'] = pCode
            form_data['captchaId'] = captchaId
            # 修改meta传递的参数信息为新的信息
            request.meta['pCode'] = pCode
            request.meta['captchaId'] = captchaId
            request.meta['proxy'] = proxy
            print(f'新的请求参数:{quote_body}--meta信息:{request.meta}')
            request = request.replace(body=quote_body, meta=request.meta)
            return request


class RewriteRetryMiddleware(RetryMiddleware):
    """ 重写重试中间件 """
    redis_client = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DB,
    )
    redis_proxy = redis.StrictRedis(
        host=settings.REDIS_PROXIES_HOST,
        port=settings.REDIS_PROXIES_PORT,
        password=settings.REDIS_PROXIES_PASSWORD,
        db=settings.REDIS_PROXIES_DB,
    )

    def delete_proxy(self, proxy):
        """ 删除代理，公司拨号代理是set """
        self.redis_proxy.srem("proxies", proxy)

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        if response.status in [403]:
            """  单独处理封IP的情况，删除代理重新请求  """
            proxy_spider = request.meta.get('proxy')
            proxy_redis = proxy_spider.split("//")[1]
            time.sleep(1)
            self.delete_proxy(proxy_redis)
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        return response

    def _retry(self, request, reason, spider):
        retries = request.meta.get('retry_times', 0) + 1

        retry_times = self.max_retry_times

        if 'max_retry_times' in request.meta:
            retry_times = request.meta['max_retry_times']

        stats = spider.crawler.stats
        if retries <= retry_times:
            logger.debug("Retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra={'spider': spider})
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust

            if isinstance(reason, Exception):
                reason = global_object_name(reason.__class__)

            stats.inc_value('retry/count')
            stats.inc_value('retry/reason_count/%s' % reason)
            return retryreq
        else:
            # 全部重试错误，要保存错误的url和参数 - start
            error_request = spider.name + ":error_urls"
            self.redis_client.sadd(error_request, request.url)
            # 全部重试错误，要保存错误的url和参数 - en
            stats.inc_value('retry/max_reached')
            logger.debug("Gave up retrying %(request)s (failed %(retries)d times): %(reason)s",
                         {'request': request, 'retries': retries, 'reason': reason},
                         extra={'spider': spider})

    def process_exception(self, request, exception, spider):
        if "ConnectionRefusedError" in repr(exception):
            proxy_spider = request.meta.get('proxy')
            proxy_redis = proxy_spider.split("//")[1]
            self.delete_proxy(proxy_redis)
            logger.info('目标计算机积极拒绝，删除代理-{}-请求url-{}开始重新请求'.format(proxy_redis, request.url))
            return request

        elif "TCPTimedOutError" in repr(exception):
            logger.debug('连接方在一段时间后没有正确答复或连接的主机没有反应')
            return request

        elif "ConnectionError" in repr(exception):
            logger.debug("连接出错，无网络")
            return request

        elif "TimeoutError" in repr(exception):
            logger.debug('请求超时-请求url-{}-重新请求'.format(request.url))
            return request

        elif "ConnectionResetError" in repr(exception):
            proxy_spider = request.meta.get('proxy')
            proxy_redis = proxy_spider.split("//")[1]
            self.delete_proxy(proxy_redis)
            logger.info(f'远程主机强迫关闭了一个现有的连接--{request.url}')
            time.sleep(3)
            return request

        elif "ResponseNeverReceived" in repr(exception):
            proxy_spider = request.meta.get('proxy')
            proxy_redis = proxy_spider.split("//")[1]
            self.delete_proxy(proxy_redis)
            time.sleep(3)
            logger.info(f'可能是请求头无法使用，没有正确的响应内容--删除代理{proxy_redis}--{request.url}')
            return request

        elif "TunnelError" in repr(exception):
            proxy_spider = request.meta.get('proxy')
            proxy_redis = proxy_spider.split("//")[1]
            self.delete_proxy(proxy_redis)
            time.sleep(3)
            logger.info(f'不清楚啥错误--删除代理{proxy_redis}--{request.url}')
            return request

        else:
            logger.error('出现其他异常:{}--等待处理'.format(repr(exception)))
