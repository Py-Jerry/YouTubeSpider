# -*- coding: utf-8 -*-
# @Time    : 2025/6/4 15:32
# @Author  : Soin
# @File    : config.py
# @Software: PyCharm
from loguru import logger
from pymongo import MongoClient
# MongoDB 连接
CLIENT = MongoClient()
DB = CLIENT["test_ytb"]
# 日志
logger.add("get_video_list.log", rotation="5 MB", encoding="utf-8", enqueue=True, retention="10 days")
