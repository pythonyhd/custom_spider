# -*- coding: utf-8 -*-
import json
import logging
import random
import time

import redis
import requests
from fake_useragent import UserAgent

from custom_spider import settings

logger = logging.getLogger(__name__)


class CaptchaProcess(object):
    """ 失信被执行人，处理验证码 """
    headers = {'User-Agent': UserAgent().random}
    redis_client = redis.StrictRedis(host=settings.REDIS_PROXIES_HOST, port=settings.REDIS_PROXIES_PORT, password=settings.REDIS_PROXIES_PASSWORD, db=settings.REDIS_PROXIES_DB)
    redis_key = 'proxies'

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

    @classmethod
    def get_captcha(cls, url, max_retry=20):
        """ 获取验证码图片 """
        while max_retry > 0:
            proxy = cls.get_proxy()
            try:
                resp = requests.get(url, headers=cls.headers, proxies=proxy, allow_redirects=False, timeout=10)
                if resp.status_code in [200, 201, 202]:
                    return {'resp': resp.content, 'proxy': proxy}
            except Exception as e:
                times = 20
                max_retry -= 1
                logger.info(f'验证码下载失败，开始第{times-max_retry}次重试--当前ip{proxy}--失败原因:{repr(e.args)}')
                if max_retry == 0:
                    logger.error('达到最大重试次数还是下载失败')

    @classmethod
    def parse_captcha(cls, img):
        """ 识别验证码 """
        resp = requests.post(url=settings.CAPTCH_URI, data=img, timeout=15)
        if resp.status_code == 200:
            code = json.loads(resp.text).get('code')
            return code
        else:
            print('验证码识别失败')

    @classmethod
    def get_proxy(cls):
        """ 获取代理IP """
        proxy = cls.redis_client.srandmember(cls.redis_key)
        if proxy:
            proxies = {
                'http': 'http://{}'.format(proxy.decode('utf-8')),
                'https': 'https://{}'.format(proxy.decode('utf-8')),
            }
            return proxies
        else:
            logger.error('代理池枯竭')
            time.sleep(10)

    def main(self):
        uuid = self.process_uuid()
        url = 'http://zxgk.court.gov.cn/shixin/captchaNew.do?captchaId={}&random={}'.format(uuid, random.random())
        cat_item = self.get_captcha(url)
        img = cat_item.get('resp')
        code = self.parse_captcha(img)
        item = dict(captchaId=uuid, code=code)
        return item


class ExecuteCaptchaProcess(CaptchaProcess):
    """被执行人验证码识别"""
    def main(self):
        uuid = self.process_uuid()
        url = 'http://zxgk.court.gov.cn/zhixing/captcha.do?captchaId={}&random={}'.format(uuid, random.random())
        cat_item = self.get_captcha(url)
        img = cat_item.get('resp')
        code = self.parse_captcha(img)
        item = dict(captchaId=uuid, code=code)
        return item


class ConsumptionCaptchaProcess(CaptchaProcess):
    """限制高消费验证码识别"""
    def main(self):
        uuid = self.process_uuid()
        url = 'http://zxgk.court.gov.cn/xgl/captchaXgl.do?captchaId={}&random={}'.format(uuid, random.random())
        cat_item = self.get_captcha(url)
        img = cat_item.get('resp')
        proxy = cat_item.get('proxy')
        code = self.parse_captcha(img)
        item = dict(captchaId=uuid, code=code, proxy=proxy)
        return item


if __name__ == '__main__':
    # 失信被执行人
    # cap = CaptchaProcess()
    # result = cap.main()
    # print(result)
    # 被执行人
    # execute = ExecuteCaptchaProcess()
    # exec = execute.main()
    # print(exec)
    # 限制高消费
    xg = ConsumptionCaptchaProcess()
    xz_gxf = xg.main()
    print(xz_gxf)