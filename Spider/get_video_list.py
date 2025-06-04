# -*- coding: utf-8 -*-
# @Time    : 2025/6/3 15:57
# @Author  : Soin
# @File    : get_video_list.py
# @Software: PyCharm
"""
is 该脚本的作用是用于获取到视频列表的
"""



import requests
class V3_API_Invoke:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    def get_data(self):

        url = 'https://youtube.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'maxResults': 50,
            'q': 'solo dance',
            'type': 'video',
            'key': self.api_key
        }
        resp = requests.get(url, params=params, headers=self.headers)
        print(resp.json())

if __name__ == '__main__':
    ytb_key = '***************************************'   # 这里自己去申请嗷

    v3_api = V3_API_Invoke(ytb_key)
    v3_api.get_data()