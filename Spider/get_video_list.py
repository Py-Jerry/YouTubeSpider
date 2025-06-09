# -*- coding: utf-8 -*-
# @Time    : 2025/6/3 15:57
# @Author  : Soin
# @File    : get_video_list.py
# @Software: PyCharm
"""
该脚本用于获取视频列表
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from youtubesearchpython import VideosSearch
import time
from config import logger, DB
from tools.decorators import retry_request


class YouTubeShortsScraper:
    def __init__(self, query):
        if "danc" in query:
            self.table = DB['dance']
        else:
            self.table = DB['sing']
        self.query = query

    @retry_request(max_retries=5)
    def get_search(self, videos_search):
        return videos_search.result()

    def check_and_insert(self, video):
        video_id = video['id']
        duration = video.get('duration', '0:00')

        if self.table.find_one({"video_id": video_id}) or DB['OK_DATA'].find_one({"video_id": video_id}):
            logger.info(f"已存在：{video_id}")
            return False

        data = {
            "video_id": video_id,
            "title": video["title"],
            "duration": duration,
            "publishedAt": video.get("publishedTime", ""),
            "channel": video.get("channel", {}).get("name", ""),
            "thumbnail": video["thumbnails"][-1]["url"] if video["thumbnails"] else "",
        }
        self.table.insert_one(data)
        logger.success(f"✅ 插入：{video_id}")
        return True

    def search_all_shorts(self):
        page_num = 1
        videos_search = VideosSearch(self.query, limit=40)

        while True:
            all_count = 0
            result = self.get_search(videos_search)
            videos = result.get("result", [])
            if not videos:
                logger.info("⚠️ 没有更多结果了。")
                break

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(self.check_and_insert, video) for video in videos]
                for future in as_completed(futures):
                    if future.result():
                        all_count += 1

            logger.success(f"[第 {page_num} 页] 收集数量：{all_count}")

            if not videos_search.next():
                logger.info("✅ 没有下一页了")
                break

            page_num += 1
            time.sleep(1)


query_list = [
    'dance shorts',
    'singing shorts',
    'viral dancer',
    'cover song',
    'tiktok dance',
    'street dance',
    'live performance singer',
    'girl singing',
    'shorts singer',
]

if __name__ == '__main__':
    for query in query_list:
        scraper = YouTubeShortsScraper(query)
        scraper.search_all_shorts()
