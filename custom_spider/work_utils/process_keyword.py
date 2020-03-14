# -*- coding: utf-8 -*-
import pymysql
import redis


MYSQL_HOST = '114.115.128.41'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PWD = 'mysql@Axinyong123'
MYSQL_DB = 'wecat_gjqyxx'
MYSQL_CHARSET = 'utf8'

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
REDIS_PWD = ''
REDIS_DB = 4
mysql_client = pymysql.connect(host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER, password=MYSQL_PWD, db=MYSQL_DB, charset=MYSQL_CHARSET)
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD, db=REDIS_DB)


def mysql_keyword_redis():
    """ 中国执行信息公开网-搜索关键词 """
    num = 0
    cursor = mysql_client.cursor()
    sql_query = """
            SELECT keyword FROM `jieba_cut_words` ORDER BY score DESC LIMIT 0,100000;
    """
    try:
        cursor.execute(sql_query)
        mysql_client.commit()
        keywords = cursor.fetchall()
        for keyword in keywords:
            num += 1
            # 失信被执行人
            # redis_client.lpush('promise_crawler:keywords', keyword[0])
            # 被执行人
            # redis_client.lpush('execute_crawler:keywords', keyword[0])
            # 限制高消费
            # redis_client.lpush('consumption_crawler:keywords', keyword[0])
            # 中华全国工商业联合会-失信被执行人
            redis_client.lpush('acfic_crawler:keywords', keyword[0])
            print('插入第{}条'.format(num))
    except Exception as e:
        mysql_client.rollback()
        print('出错:{}'.format(repr(e)))
        mysql_keyword_redis()
    finally:
        cursor.close()
        mysql_client.close()


if __name__ == '__main__':
    mysql_keyword_redis()