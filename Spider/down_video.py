# -*- coding: utf-8 -*-
# @Time    : 2025/6/4 10:27
# @Author  : Soin
# @File    : down_video.py
# @Software: PyCharm
import yt_dlp
from pathlib import Path
from config import logger


class YouTubeVideoDownloader:
    def __init__(self, video_id, theme='temp'):
        self.video_id = video_id  # 视频id
        self.theme = theme  # 视频主题
        self.video_url = f'https://www.youtube.com/shorts/{video_id}'
        # D盘的路径使用 pathlib.Path 构建路径
        self.save_dir_path = Path(r'D:\YTBVideo', theme)
        # 创建这个路径
        self.save_dir_path.mkdir(parents=True, exist_ok=True)

    def is_valid_video(self, info):
        """
            这个函数实现的是对视频的信息进行判断
        :param info: 视频的信息
        :return:
        """
        # 判断时长
        duration = info.get('duration', 0)
        # 如果时长不在10-30秒之间则跳过
        if not (10 <= duration <= 30):
            return False, "⏱️ 不符合时长要求"
        # 筛选出1080P及以上的
        valid_streams = [
            f for f in info['formats']
            if f.get('vcodec') != 'none'
               and f.get('acodec') != 'none'
               and f.get('height', 0) >= 1080
        ]
        # 如果这个列表为空则跳过
        if not valid_streams:
            return False, "❌ 没有1080P及以上带音频的视频"
        # 如果不是竖屏则跳过
        is_vertical = any(f.get('height', 0) > f.get('width', 0) * 1.2 for f in valid_streams)
        if not is_vertical:
            return False, "📺 不是竖屏视频"

        # 如果通过了前面的层层筛选则选一个画质最高的
        best_format = sorted(valid_streams, key=lambda x: x.get('height', 0), reverse=True)[0]
        return True, best_format['format_id']
    def check_video(self):
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            # 获取视频信息
            info = ydl.extract_info(self.video_url, download=False)
            is_valid, result = self.is_valid_video(info)
            # 判断是否合格
            if not is_valid:
                logger.info(f"😭跳过：{result}")
                return result

    def download_if_valid(self):
        """
        这个函数实现的是访问视频链接，并获取到视频的信息，如果合格则下载
        :return:
        """

        # with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        #     # 获取视频信息
        #     info = ydl.extract_info(self.video_url, download=False)
        #     is_valid, result = self.is_valid_video(info)
        #     # 判断是否合格
        #     if not is_valid:
        #         logger.info(f"😭跳过：{result}")
        #         return
            # 如果是合格的视频则下载
        format_id = self.check_video()

        output_path = self.save_dir_path / f"{video_id}.%(ext)s"  # pathlib.Path 自动拼接路径

        print(f"✅ 合格视频，准备下载：{video_id}")
        print(f"📁 保存路径：{output_path}")

        # Step 4: 配置 yt_dlp 下载
        ydl_opts = {
            'format': f'{format_id}+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            'outtmpl': str(output_path),  # 注意要转为 str
            'quiet': False,
            'no_warnings': True,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
            ydl_download.download([self.video_url])


# 示例
if __name__ == '__main__':
    video_id = "KoDsOH0WtWs"
    # test_url =
    ytvd = YouTubeVideoDownloader(video_id)
    ytvd.download_if_valid()
