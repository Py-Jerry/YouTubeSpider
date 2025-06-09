# -*- coding: utf-8 -*-
# @Time    : 2025/6/7 21:29
# @Author  : Soin
# @File    : Spider+down.py
# @Software: PyCharm
"""
该代码实现的功能是将油管视频下载和获取两个整合到一起
该代码将会实现：
    1. 边搜索载边下载
    2. 每个关键字将只下载20条视频
"""
from YouTube_Serch import YouTubeSearch
from down_video import main
from config import logger, DB


class YouTubeVideoSpider:
    def __init__(self, keyword, theme='temp'):
        self.keyword = keyword
        self.theme = theme
        self.video_list = self.get_video_list()
        self.down_num = 0

    def get_video_list(self):
        youtube_search = YouTubeSearch(self.keyword, self.theme)
        return youtube_search.get_main_page()

    def down_video(self):
        for video in self.video_list:
            if self.down_num >= 20:
                break
            try:
                if main(video['video_id'], self.theme):
                    logger.success(f"{video['video_id']}下载成功")
                    DB[self.theme].insert_one(video)
                else:
                    logger.warning("该条视频被视为不合格或不可下载")
                    DB['unqualified_video'].insert_one(video)
            except Exception as e:
                logger.error(f"{video['video_id']}下载失败:{e}")
                continue

    def main(self):
        self.get_video_list()
        print(self.video_list)
        self.down_video()
        logger.success(f"{self.keyword}前20条下载完成")


# def main(keyword,theme='temp'):

if __name__ == '__main__':
    youtube_spider = YouTubeVideoSpider("dance", 'test')
    youtube_spider.main()
    # with open("../temp/dance.txt",'r',encoding='utf-8') as f:
    #     for keyword in f.read().split('\n')[500:]:
    #         keyword = keyword.replace(" ","+")
    #         youtube_spider = YouTubeVideoSpider(keyword, 'test')
    #         youtube_spider.main()