# -*- coding: utf-8 -*-
# @Time    : 2025/6/4 10:27
# @Author  : Soin
# @File    : down_video.py
# @Software: PyCharm
import yt_dlp
from pathlib import Path
import datetime
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class YouTubeVideoDownloader:
    def __init__(self, video_id, theme='temp'):
        self.video_id = video_id
        self.theme = theme
        self.video_url = f'https://www.youtube.com/shorts/{video_id}'
        print(f"视频链接：{self.video_url}")

        # 构建保存路径
        today = datetime.date.today().strftime('%Y-%m-%d')
        self.save_dir_path = Path(f'D:/YTBVideo/{today}', theme)
        self.save_dir_path.mkdir(parents=True, exist_ok=True)

    def is_valid_video(self, info):
        """检查视频是否符合下载要求"""
        # 检查时长（10-30秒）
        duration = info.get('duration', 0)
        if not (10 <= duration <= 30):
            return False, f"⏱️ 不符合时长要求: {duration}秒"

        # 筛选1080P+的视频流
        valid_streams = [
            f for f in info['formats']
            if isinstance(f.get('height'), int) and f['height'] >= 1080 and isinstance(f.get('width'), int) and f['width'] >= 1080
               and f.get('vcodec') != 'none'
        ]
        if not valid_streams:
            return False, "❌ 没有符合条件的高清视频格式"

        # 检查是否有可用音频流
        audio_streams = [
            f for f in info['formats']
            if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
        ]
        if not audio_streams:
            return False, "❌ 没有可用的音频流"

        # 检查竖屏比例（9:16 ± 0.03）
        target_ratio = 9 / 16
        tolerance = 0.03
        filtered_streams = [
            f for f in valid_streams
            if abs(f['width'] / f['height'] - target_ratio) <= tolerance
        ]
        if not filtered_streams:
            return False, "📱 不符合抖音比例要求（9:16 ± 0.03）"

        # 选择分辨率最高的视频流
        best_video = max(filtered_streams, key=lambda x: x['width'] * x['height'])
        return True, best_video['format_id']

    def check_video(self):
        """获取最佳视频和音频格式ID"""
        ydl_opts = {
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                logger.info("正在获取视频信息...")
                info = ydl.extract_info(self.video_url, download=False)
            except Exception as e:
                logger.error(f"获取视频信息失败: {e}")
                return None, None

            is_valid, video_format_id = self.is_valid_video(info)
            if not is_valid:
                logger.info(f"跳过视频: {video_format_id}")
                return None, None

            # 筛选最佳音频流（优先选择AAC编码或MP4封装）
            audio_streams = [
                f for f in info['formats']
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
                   and (f.get('ext') == 'mp4' or f.get('acodec') == 'aac')
            ]

            # 如果没有AAC/MP4格式，退而求其次选择其他音频流
            if not audio_streams:
                audio_streams = [
                    f for f in info['formats']
                    if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
                ]

            if not audio_streams:
                logger.error("未找到可用的音频流")
                return video_format_id, None

            # 根据比特率或文件大小选择最佳音频流
            def get_audio_quality(f):
                abr = f.get('abr', 0)
                filesize = f.get('filesize', 0)
                return int(abr) if abr is not None else filesize

            best_audio = max(audio_streams, key=get_audio_quality)
            return video_format_id, best_audio['format_id']

    def download_if_valid(self):
        """下载符合条件的视频"""
        output_path = str(self.save_dir_path / f"{self.video_id}.mp4")
        video_format_id, audio_format_id = self.check_video()

        if not video_format_id or not audio_format_id:
            logger.error("未找到合适的视频或音频格式")
            return False

        logger.info(f"✅ 视频合格，准备下载: {self.video_id}")
        logger.info(f"📁 保存路径: {output_path}")

        ydl_opts = {
            'format': f"{video_format_id}+{audio_format_id}",
            'outtmpl': output_path,
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': False,
            'overwrites': True,
            'ffmpeg_location': r'E:\html_to_pdf\ffmpeg-7.1-essentials_build\bin\ffmpeg.exe',
            'verbose': True,
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4'
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True
                }
            ],
            # 关键参数：强制音频转码为AAC
            'postprocessor_args': {
                'ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental']
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.video_url])
            logger.info(f"🎉 下载完成: {output_path}")
            return True
        except Exception as e:
            logger.error(f"❌ 下载失败: {e}")
            return False


def main(video_id, theme='temp'):
    """主函数：下载单个视频"""
    downloader = YouTubeVideoDownloader(video_id, theme)
    return downloader.download_if_valid()


if __name__ == '__main__':
    # 示例：下载指定ID的视频
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        theme = sys.argv[2] if len(sys.argv) > 2 else 'temp'
        main(video_id, theme)
    else:
        # 默认下载示例视频
        main('0oqTjXczmMY')