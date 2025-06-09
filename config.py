# -*- coding: utf-8 -*-
# @Time    : 2025/6/4 15:32
# @Author  : Soin
# @File    : config.py
# @Software: PyCharm
from loguru import logger
from pymongo import MongoClient
# MongoDB 连接
CLIENT = MongoClient(
    'mongodb://root:Aliyun_Mongo_20250218@dds-2vc3c96a7e797ee41197-pub.mongodb.cn-chengdu.rds.aliyuncs.com:3717,dds-2vc3c96a7e797ee42971-pub.mongodb.cn-chengdu.rds.aliyuncs.com:3717/admin?replicaSet=mgset-1150525521')
DB = CLIENT["test_ytb"]
# 日志
logger.add("get_video_list.log", rotation="5 MB", encoding="utf-8", enqueue=True, retention="10 days")
