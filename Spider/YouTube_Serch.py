# -*- coding: utf-8 -*-
# @Time    : 2025/6/4 18:19
# @Author  : Soin
# @File    : YouTube_Serch.py
# @Software: PyCharm
import random
import time
import requests, json, re
from config import logger
from datetime import datetime
from tools.decorators import retry_request
from requests.adapters import HTTPAdapter, Retry
from requests.exceptions import ChunkedEncodingError, RequestException
import config

class YouTubeSearch:
    def __init__(self, query,video_type):
        self.query = query
        self.db = config.DB
        self.table = self.db[video_type]
        self.get_timestamp = self.get_timestamp()
        self.video_type = video_type
        self.video_list = []


    # def requests_post(self):
    # 该函数生成时间戳
    def get_timestamp(self):

        timestamp_ms = int(datetime.now().timestamp() * 1000)
        return timestamp_ms

    @retry_request(max_retries=3)
    def extract_shorts_tokens(self, data):

        for d in data['onResponseReceivedCommands']:
            # print(d)
            next_token = re.findall(r"'token':(.*?)',", str(d))[0].replace(' ', '')[1:]
            next_clickTrackingParams = re.findall(r"'clickTrackingParams': '(.*?)',", str(d))[-1]
            return {'next_token': next_token, 'next_clickTrackingParams': next_clickTrackingParams}

    def extract_all_video_ids(self, data):
        """
        从 YouTube 搜索结果的 JSON 数据中提取所有 videoId。
        :param data: JSON数据
        :return: videoId 列表
        """
        video_ids = []

        def search(obj):
            # ['onResponseReceivedCommands'][0]
            if isinstance(obj, dict):
                if 'videoRenderer' in obj and isinstance(obj['videoRenderer'], dict):
                    video_id = obj['videoRenderer'].get('videoId')
                    if video_id:
                        video_ids.append(obj['videoRenderer'])
                for v in obj.values():
                    search(v)
            elif isinstance(obj, list):
                for item in obj:
                    search(item)

        search(data)
        return video_ids

    # @ retry_request(max_retries=3)

    def get_search_query(self, context, token, clickTrackingParams):

        # 初始化 requests session + 重试策略
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        seen_ids = set()
        total_count = 0
        duplicate_count = 0
        success_count = 0

        cookies = {}
        headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://www.youtube.com',
            'priority': 'u=1, i',
            'referer': f'https://www.youtube.com/results?search_query={self.query}',
            'user-agent': 'Mozilla/5.0',
            'x-youtube-client-name': '1',
            'x-youtube-client-version': '2.20250604.00.00',
        }
        params = {'prettyPrint': 'false'}

        while token:

            time.sleep(random.randint(3, 5))

            if context['clickTracking']['clickTrackingParams'] is None:
                context['clickTracking']['clickTrackingParams'] = clickTrackingParams

            adSignalsInfo = {
                'params': [
                    {'key': 'dt', 'value': str(self.get_timestamp)},
                    {'key': 'flash', 'value': '0'},
                    {'key': 'frm', 'value': '0'},
                    {'key': 'u_tz', 'value': '480'},
                    {'key': 'u_his', 'value': '3'},
                    {'key': 'u_h', 'value': '1080'},
                    {'key': 'u_w', 'value': '1920'},
                    {'key': 'u_ah', 'value': '1032'},
                    {'key': 'u_aw', 'value': '1920'},
                    {'key': 'u_cd', 'value': '24'},
                    {'key': 'bc', 'value': '31'},
                    {'key': 'bih', 'value': '945'},
                    {'key': 'biw', 'value': '581'},
                    {'key': 'brdim', 'value': '0,0,0,0,1920,0,1920,1032,596,945'},
                    {'key': 'vis', 'value': '1'},
                    {'key': 'wgl', 'value': 'true'},
                    {'key': 'ca_type', 'value': 'image'},
                ],
            }

            context.update({'adSignalsInfo': adSignalsInfo})
            json_data = {'context': context, 'continuation': token}

            try:
                response = session.post(
                    'https://www.youtube.com/youtubei/v1/search',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    json=json_data,
                    timeout=15,
                )
                response.raise_for_status()
                datas = response.json()
            except (ChunkedEncodingError, RequestException) as e:
                logger.warning(f"请求失败：{e}")
                break
            except Exception as e:
                logger.error(f"解析响应失败：{e}")
                break
            finally:
                context['clickTracking']['clickTrackingParams'] = None
                context.pop('adSignalsInfo', None)

            for d in self.extract_all_video_ids(datas):
                video_id = d.get('videoId')
                list_collection_names = self.db.list_collection_names()
                if 'unqualified_video' not in list_collection_names:
                    pass  # 如果没有这个表就先不管
                else:
                    # 检查这个视频存不存在
                    if self.db['unqualified_video'].find_one({'video_id': video_id}):
                        # 如果这个视频存在于不合格视频里面就跳过
                        logger.debug("该视频已被视为不合格视频")
                        continue
                    elif self.db[self.video_type].find_one({'video_id': video_id}):
                        logger.debug('该视频已存在数据库中')
                        continue
                total_count += 1

                if not video_id:
                    continue
                if video_id in seen_ids:
                    duplicate_count += 1
                    continue
                seen_ids.add(video_id)
                video_data = {
                    "video_id": video_id,
                    "title": ((((d.get('title') or {}).get('accessibility') or {}).get('accessibilityData') or {}).get(
                        'label')),
                    "duration": ((d.get('publishedTimeText') or {}).get('simpleText')),
                    "publishedAt": ((d.get('publishedTimeText') or {}).get('simpleText')),
                    "thumbnail": (((d.get('thumbnail') or {}).get('thumbnails') or [{}])[-1].get('url')
                                  if (d.get('thumbnail') or {}).get('thumbnails') else None)
                }
                # 如果有名字叫unqualified_video 的表

                self.video_list.append(video_data)
                logger.success(f"成功获取视频：{video_data}")
                success_count += 1
            tokens = self.extract_shorts_tokens(datas)

            if not tokens:
                break

            # 准备下一轮
            token = tokens.get('next_token')
            clickTrackingParams = tokens.get('next_clickTrackingParams')

    @retry_request(max_retries=3)
    def get_main_page(self):
        token, clickTrackingParams = '', ''
        params = {
            'search_query': self.query, 'sttick': '0'
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9',
            'priority': 'u=0, i',
            'referer': f'https://www.youtube.com/results?search_query={self.query}',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-arch': '"x86"',
            'sec-ch-ua-bitness': '"64"',
            'sec-ch-ua-form-factors': '"Desktop"',
            'sec-ch-ua-full-version': '"134.0.6998.118"',
            'sec-ch-ua-full-version-list': '"Chromium";v="134.0.6998.118", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.118"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"19.0.0"',
            'sec-ch-ua-wow64': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'service-worker-navigation-preload': 'true',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-browser-channel': 'stable',
            'x-browser-copyright': 'Copyright 2025 Google LLC. All rights reserved.',
            'x-browser-validation': 'wTKGXmLo+sPWz1JKKbFzUyHly1Q=',
            'x-browser-year': '2025',
            'x-client-data': 'CKm1yQEIl7bJAQiitskBCKmdygEI7/XKAQiVocsBCJGjywEIhaDNAQjk7c4BCKTyzgE=',
            # 'cookie': 'VISITOR_INFO1_LIVE=10FcWFBVZxM; VISITOR_PRIVACY_METADATA=CgJKUBIEGgAgMA%3D%3D; PREF=tz=Asia.Shanghai&f7=100&f6=40000000; HSID=AVgkh2yHYhTtSei1g; SSID=AD9AYetUAk-iFMvQ2; APISID=DN0Z1pfDcuOfRKeV/AaOCIDCyQNE1qlA2v; SAPISID=qqzDv_T005PV8cGF/Ad1DBZ0188L9AP5TE; __Secure-1PAPISID=qqzDv_T005PV8cGF/Ad1DBZ0188L9AP5TE; __Secure-3PAPISID=qqzDv_T005PV8cGF/Ad1DBZ0188L9AP5TE; YSC=FKtvQGprgJo; SID=g.a000xQhG6lBvcrLakMpW3CmIhmbaRiOHU3-HBDBESfNs11DNd-OaxD7wbCmwaXzr3LSSfJ0E3QACgYKAb4SARMSFQHGX2MiP6gaWQeJc2RdUv0prNa4JxoVAUF8yKo5K2C6TtOU9sJjc64R0ZNP0076; __Secure-1PSID=g.a000xQhG6lBvcrLakMpW3CmIhmbaRiOHU3-HBDBESfNs11DNd-Oal17W98F9V9SHBykYJ30begACgYKAVYSARMSFQHGX2MifEwEaHxeECWgRXkBV3WaFhoVAUF8yKpaoATBNHA3L08XOrnPWW_w0076; __Secure-3PSID=g.a000xQhG6lBvcrLakMpW3CmIhmbaRiOHU3-HBDBESfNs11DNd-Oa6T7g4pJO3O0zfauW9QitCAACgYKAaISARMSFQHGX2MiC2IedmvzBILfBlFAxx0hjhoVAUF8yKrynjnOH1kfPOVLAISEbJ9G0076; LOGIN_INFO=AFmmF2swRQIgPLKnJjpNPmV_DAOTXt9z0XBoYTP2TBmhGRGGRt94mjUCIQCO3kbK85oAYhrFmeaYqFqQQ7vTEGHXI_hylcZYQMlqIQ:QUQ3MjNmeWpiOWo2dGFTRlVDWmg2eGVYVlhDXzBreUdXT21aZHpSQ251VkpuOFNPa1ZjU1lxWU9EdUItT05IZGpZRjNxWWwyYmdKWGk4cGo5eTVVa250eFIwS2RYVk5HMFJwWElFTUdKbUdYOHJmYVBjX2N4WWxFaE9tQmJmX2o1LW04VlVqanBIR3NyeFViLU05OE0zN3RIYjFFdjFkVVlB; __Secure-ROLLOUT_TOKEN=CKbUodCquYCJLBC79eiyo5aMAxjzjqLaz9mNAw%3D%3D; __Secure-1PSIDTS=sidts-CjEB5H03P38MqpY1UpYFVRMXNoZ7knp8LHh-vMMG4hVMmTExqUKhaOw9XwC2RntZ2I54EAA; __Secure-3PSIDTS=sidts-CjEB5H03P38MqpY1UpYFVRMXNoZ7knp8LHh-vMMG4hVMmTExqUKhaOw9XwC2RntZ2I54EAA; SIDCC=AKEyXzUU5Z7MfxL35bB82w-OwC23jTocYMBQ-LBoAFv4tB6QTV3jK9E02PJAlhfIdqYooSj6Yg; __Secure-1PSIDCC=AKEyXzU9wEZk-lBdiUnGDE4wyiU0SlNJEQ0rTQo5iG98kE3Xhtb1aS3aEPpZZHtR4_5yZ6l7fkM; __Secure-3PSIDCC=AKEyXzVAh08YiG7GyiOxG3IpXQV8uATirNcuOCk-BJeZuhzYcuPxxYZeVO81jBiA9c_TRBHDneM; ST-cqm4f=session_logininfo=AFmmF2swRgIhAI0TMABF60Qfl4INXPj0Doa-uz8C9BLufiVLU_k29TUxAiEAjhHw237zFIcRRtXBPdGgwzliZDOlS5jZsCVPl8CtLbE%3AQUQ3MjNmekUwbWFreDZrX1oxMU1EWHB5VlMzLXR4aGJZcF9yQUpqNVd5M1loSFI5VDl0RUFySTNkRmdGYUd2QmZ0SGZ0eUc4cWNnWlVTZ0hZYVplWVRwSFlyN1lkU3VybHlzYjJvUzNncmh1QXQ3WjQ1UDVkdDVxRUg2REtzdEw2UFpETEVwNTJRSTA5WXNqZGhxbUdjc0MzM2czZktSa2RR',
        }
        response = requests.get('https://www.youtube.com/results', params=params, headers=headers)
        ytInitialData = re.findall(r'var ytInitialData = (.*?);</script>', response.text)

        pattern = r'ytcfg\.set\(\s*({.*?})\s*\);'
        matches = re.findall(pattern, response.text, re.DOTALL)
        if matches:
            ytcfg = json.loads(matches[0])
        else:
            return None
        context = ytcfg['INNERTUBE_CONTEXT']
        coldConfigData = ytcfg['RAW_COLD_CONFIG_GROUP']['configData']
        SERIALIZED_COLD_HASH_DATA = ytcfg['SERIALIZED_COLD_HASH_DATA']
        SERIALIZED_HOT_HASH_DATA = ytcfg['SERIALIZED_HOT_HASH_DATA']
        new_configInfo = {
            'appInstallData': context['client']['configInfo']['appInstallData'],
            'coldConfigData': coldConfigData,
            'coldHashData': SERIALIZED_COLD_HASH_DATA,
            'hotHashData': SERIALIZED_HOT_HASH_DATA,
        }
        context['client']['configInfo'] = new_configInfo

        searchHeaderRenderer = json.loads(ytInitialData[0])['header']['searchHeaderRenderer']
        chips = searchHeaderRenderer['chipBar']['chipCloudRenderer']['chips']
        for chip in chips:
            if chip['chipCloudChipRenderer']['text']['simpleText'] == 'Shorts':
                clickTrackingParams = chip['chipCloudChipRenderer']['navigationEndpoint']['clickTrackingParams']
                token = chip['chipCloudChipRenderer']['navigationEndpoint']['continuationCommand']['token']
                break
        if self.get_search_query(context=context, token=token, clickTrackingParams=clickTrackingParams) == None:
            return self.video_list


# def main(q):
#     yts = YouTubeSearch(q)
#     logger.debug(yts.get_main_page())


if __name__ == '__main__':
    # with ThreadPoolExecutor(max_workers=9) as executor:
    yts = YouTubeSearch('baby','test')
    yts.get_main_page()
    # main('dance')

    # get_search_query(token)
