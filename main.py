import requests
import time
import json
import os
from bs4 import BeautifulSoup
from pprint import pprint

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' \
             '(KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'

BASE_DIR = os.path.dirname(__file__)


class Faktakontroll:
    def __init__(self):
        self.refresh_token = None
        self.access_token = None
        self.read_config()

    def read_config(self):
        with open(os.path.join(BASE_DIR, 'cache', 'config.json'), encoding='utf-8') as f:
            tokens = json.load(f)
            self.refresh_token = tokens['refreshToken']
            self.access_token = tokens['accessToken']

    def write_config(self):
        tokens = {
            'refreshToken': self.refresh_token,
            'accessToken': self.access_token
        }

        with open(os.path.join(BASE_DIR, 'cache', 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2)

    def refresh_tokens(self):
        cookies = {
            'ext_name': 'ojplmecpdpgccookcobabopnaifgidhf',
            'user': 'true',
        }

        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'X-Initialized-At': str(int(time.time() * 1000)),
            'DNT': '1',
            'User-Agent': USER_AGENT,
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.faktakontroll.se',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.faktakontroll.se/app/sok',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        data = f'"{self.refresh_token}"'

        try:
            response = requests.post('https://www.faktakontroll.se/app/api/auth/refresh', headers=headers,
                                     cookies=cookies,
                                     data=data)
            tokens = response.json()
            self.refresh_token = tokens['refreshToken']
            self.access_token = tokens['accessToken']
            self.write_config()
            print(tokens)
        except Exception as e:
            print(f'error while refreshing tokens: {e}')

    def search(self):
        cookies = {
            'ext_name': 'ojplmecpdpgccookcobabopnaifgidhf',
            'user': 'true',
        }

        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'X-Initialized-At': str(int(time.time() * 1000)),
            'X-Auth-Token': self.access_token,
            'User-Agent': USER_AGENT,
            'DNT': '1',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://www.faktakontroll.se',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.faktakontroll.se/app/sok?vad=Florav%C3%A4gen%201,%20Nyn%C3%A4shamn&typ=',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        data = {
            "searchString": "Florav\xE4gen 1, Nyn\xE4shamn",
            "filterType": "p",
            "subscriptionRefNo": "20.750.025.01"
        }

        response = requests.post('https://www.faktakontroll.se/app/api/search', headers=headers, cookies=cookies,
                                 json=data)

        # status code 500 when access token expires
        print(response)
        with open('resp.json', 'w', encoding='utf-8') as f:
            json.dump(response.json(), f, indent=2)

    def filter_results(self):
        """
        if area data present in faktakontroll result then check otherwise ignore result
        if floor data present in faktakontroll result then check otherwise ignore result
        """
        pass


class Hemnet:
    def __init__(self):
        self.location_id = None

    @staticmethod
    def search_keywords(keyword):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': '',
            'DNT': '1',
            'User-Agent': USER_AGENT,
            'X-Requested-With': 'XMLHttpRequest',
        }

        response = requests.get(f'https://www.hemnet.se/locations/show?q={keyword}',
                                headers=headers)
        try:
            return response.json()[0]['id']
        except Exception as e:
            print(e)
            return None

    def search(self, keyword, page_number=1):
        if not self.location_id:
            self.location_id = self.search_keywords(keyword)
        print(f'{self.location_id}')

        headers = {
            'authority': 'www.hemnet.se',
            'user-agent': USER_AGENT,
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
        }
        params = {
            'by': 'creation',
            'housing_form_groups[]': ['houses', 'row_houses', 'apartments'],
            'location_ids[]': str(self.location_id),
            'order': 'desc',
            'page': str(page_number),
            'preferred_sorting': 'true',
        }

        res = requests.get('https://www.hemnet.se/bostader', headers=headers, params=params)
        print(res)
        soup = BeautifulSoup(res.content, 'html.parser')

        # list all the search results in current page
        lis = soup.find_all('li', {'class': 'normal-results__hit js-normal-list-item'})

        results = []

        # get the data for each search result
        for li in lis:
            try:
                address_and_floor = li.find('h2', {'class': 'listing-card__street-address qa-listing-title'}
                                            ).text.strip()
                # get the address and floor value separately
                adr_flr = address_and_floor.split(',')
                if len(adr_flr) > 1:
                    # first data in the coma separated values would be address
                    address = adr_flr[0].strip()

                    # check if floor data is present in rest of the values.
                    # default value of floor is None when no floor data present
                    floor = None
                    for flr in adr_flr[1:]:
                        if 'tr' in flr:
                            floor = flr.strip().removesuffix('tr').strip()
                            break
                else:
                    address = address_and_floor.strip()
                    floor = None

                location = li.find('span', {'class': 'listing-card__location-name'}).text.strip()
                city = location.split(',')[-1].strip()

                # get the area value if present
                attribs_div = li.find('div', {'class': 'listing-card__attributes-row'})
                attribs = attribs_div.find_all('div', {'class': 'listing-card__attribute'})
                area = None
                for attrib in attribs:
                    if 'm²' in attrib.text:
                        area = attrib.text.strip().removesuffix('m²').strip()
                        break
                result_id = json.loads(li['data-gtm-item-info'])['id']

                results.append({
                    'id': result_id,
                    'address': address,
                    'city': city,
                    'area': self.parse_area(area),
                    'floor': floor,
                    'complete': False
                })
            except Exception as e:
                # print(e)
                # if any required data isn't present for a result then it will be skipped
                pass
        return results

    @staticmethod
    def parse_area(area_string):
        # remove any extra characters from the area value
        area_string = area_string.strip().removesuffix('m²').strip().replace(',', '.')

        """
        # sometimes the area is displayed as addition of multiple values.
        # parse and add those numbers in that case
        if '+' in area_string:
            try:
                area_string = str(sum(map(int, area_string.split('+'))))
            except:
                pass
        """

        # faktakontroll.se lists only the first value if hemnet shows in "a + b" format
        # so return the first value if the area has +  in it
        if '+' in area_string:
            area_string = area_string.split('+')[0].strip()

        return area_string

    def save_schema(self):
        pass

    def load_schema(self):
        pass


if __name__ == '__main__':
    hemnet = Hemnet()
    pprint(hemnet.search('st', 1))
