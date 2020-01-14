# -*- coding: utf-8 -*-
import redis

from custom_spider import settings


class RandomProxy:
    redis_proxy = redis.StrictRedis(
        host=settings.REDIS_PROXIES_HOST,
        port=settings.REDIS_PROXIES_PORT,
        password=settings.REDIS_PROXIES_PASSWORD,
        db=settings.REDIS_PROXIES_DB,
    )

    def get_proxy(self, url):
        ip_port = self.redis_proxy.srandmember('proxies')
        proxies = {
            'http': 'http://{}'.format(ip_port.decode('utf-8')),
            'https': 'https://{}'.format(ip_port.decode('utf-8')),
        }
        if url.startswith('http'):
            return proxies.get('http')
        else:
            return proxies.get('https')


if __name__ == '__main__':
    url = 'http://www.baidu.com'
    conn = RandomProxy()
    ip = conn.get_proxy(url)
    print(ip)