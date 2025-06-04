# -*- coding: utf-8 -*-
# @Time    : 2025/6/3 15:57
# @Author  : Soin
# @File    : get_video_list.py
# @Software: PyCharm
"""
is 该脚本的作用是用于获取到视频列表的
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from youtubesearchpython import VideosSearch
import time
from down_video import YouTubeVideoDownloader
from config import logger, DB
from tools.decorators import retry_request

class YouTubeShortsScraper:
    def __init__(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=32)  # 控制线程数量

    @retry_request(max_retries=5)
    def get_search(self, videos_search):
        return videos_search.result()

    def check_and_process_video(self, video, query):
        video_id = video['id']
        duration = video.get('duration', '0:00')

        # 调用 check_video（这个是最慢的）
        if not YouTubeVideoDownloader(video_id).check_video():
            return None

        if DB[query].find_one({"video_id": video_id}):
            logger.info(f"已存在：{video_id}")
            return None

        data = {
            "video_id": video_id,
            "title": video["title"],
            "duration": duration,
            "publishedAt": video.get("publishedTime", ""),
            "channel": video.get("channel", {}).get("name", ""),
            "thumbnail": video["thumbnails"][-1]["url"] if video["thumbnails"] else "",
        }

        DB[query].insert_one(data)
        return data

    def search_all_shorts(self, query):
        page_num = 1
        videos_search = VideosSearch(query, limit=40)

        while True:
            result = self.get_search(videos_search)
            videos = result.get("result", [])
            if not videos:
                logger.info("⚠️ 没有更多结果了。")
                break

            futures = []
            for video in videos:
                futures.append(self.thread_pool.submit(self.check_and_process_video, video, query))

            count = 0
            for future in as_completed(futures):
                res = future.result()
                if res:
                    count += 1

            logger.success(f"[第 {page_num} 页] ✅ 收集成功数量：{count}")

            if not videos_search.next():
                logger.info("✅ 没有下一页了")
                break

            page_num += 1
            time.sleep(1)  # 限速

if __name__ == '__main__':
    scraper = YouTubeShortsScraper()
    scraper.search_all_shorts(query="dance")
