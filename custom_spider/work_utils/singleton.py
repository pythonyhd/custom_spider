# -*- coding: utf-8 -*-
import time

import redis

from custom_spider import settings


class ProcessProxy(object):
    """IP产生器，单例模式，一直是一个IP"""
    instant = None
    flag = True
    redis_client = redis.StrictRedis(host=settings.REDIS_PROXIES_HOST, port=settings.REDIS_PROXIES_PORT, password=settings.REDIS_PROXIES_PASSWORD, db=settings.REDIS_PROXIES_DB)
    redis_key = 'proxies'

    def __new__(cls, *args, **kwargs):
        if cls.instant is None:
            cls.instant = super().__new__(cls)
        return cls.instant

    def __init__(self):
        if not ProcessProxy.flag:
            return
        self.proxy = self.get_proxy()
        ProcessProxy.flag = False
        # print('这个类已经被初始化了')

    def get_proxy(self):
        proxy = self.redis_client.srandmember(self.redis_key)
        if proxy:
            proxies = {
                'http': 'http://{}'.format(proxy.decode('utf-8')),
                'https': 'https://{}'.format(proxy.decode('utf-8')),
            }
            return proxies
        else:
            time.sleep(10)


if __name__ == '__main__':
    # d = ProcessProxy()
    # print('d对象所在的内存地址是 %d, B类所在的内存地址是 %d' % (id(d), id(ProcessProxy)))
    # e = ProcessProxy()
    # print('e对象所在的内存地址是 %d, B类所在的内存地址是 %d' % (id(e), id(ProcessProxy)))
    # f = ProcessProxy()
    # print('f对象所在的内存地址是 %d, B类所在的内存地址是 %d' % (id(f), id(ProcessProxy)))
    # print(d.proxy)
    # print(e.proxy)
    # print(f.proxy)
    for keyword in ['赵', '钱', '孙']:
        p = ProcessProxy().proxy
        print(p)