import config
import requests
import time


class Faktakontroll:
    def __init__(self):
        self.refresh_token = config.refresh_token

    def search(self):
        cookies = {
            'ext_name': 'ojplmecpdpgccookcobabopnaifgidhf',
            'user': 'true',
        }

        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'X-Initialized-At': int(time.time() * 1000),
            'X-Auth-Token': config.access_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/86.0.4240.75 Safari/537.36',
            'DNT': '1',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.faktakontroll.se',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.faktakontroll.se/app/sok?vad=Florav%C3%A4gen%201,%20Nyn%C3%A4shamn&typ=',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        data = '{"searchString":"Florav\xE4gen 1, Nyn\xE4shamn","filterType":"","subscriptionRefNo":"20.750.025.01"}'

        response = requests.post('https://www.faktakontroll.se/app/api/search', headers=headers, cookies=cookies,
                                 data=data)
