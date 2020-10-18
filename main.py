import re

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

    @property
    def current_time(self):
        return str(int(time.time() * 1000))

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
        except Exception as e:
            print(f'error while refreshing tokens: {e}')

    def search(self, address):
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
            'Referer': 'https://www.faktakontroll.se/app/sok',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        }

        data = {
            "searchString": address,
            "filterType": "p",
            "subscriptionRefNo": "20.750.025.01"
        }

        response = requests.post('https://www.faktakontroll.se/app/api/search',
                                 headers=headers, cookies=cookies, json=data)

        # refresh the tokens when their validity expires
        if response.status_code != 200:
            print('faktakontroll token expired. refreshing token...')
            self.refresh_tokens()
            return self.search(address)

        data = response.json()
        results = data['hits']
        result_ids = [result['id'] for result in results if result.get('individual')]
        print(f'{len(result_ids)} matches found')

        for result_id in result_ids:
            individual_result = self.search_individual(result_id)

        ## save the response as e json file
        # with open('resp.json', 'w', encoding='utf-8') as f:
        #     json.dump(response.json(), f, indent=2)

    def search_individual(self, result_id):
        cookies = {
            'ext_name': 'ojplmecpdpgccookcobabopnaifgidhf',
            'user': 'true',
        }

        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'X-Initialized-At': self.current_time,
            'X-Auth-Token': self.access_token,
            'User-Agent': USER_AGENT,
            'DNT': '1',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://www.faktakontroll.se/app/sok',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,sv;q=0.6',
        }

        params = {'subscriptionRefNo': '20.750.025.01'}

        try:
            response = requests.get(f'https://www.faktakontroll.se/app/api/search/entity/{result_id}',
                                    headers=headers, params=params, cookies=cookies)

            user_data = response.json()['individual']

            # get phone page_number
            phone_number_list = user_data['phoneNumbers']
            try:
                phone_numbers = [phone_number['phoneNumber'] for phone_number in phone_number_list]
            except:
                phone_numbers = []

            # get floor number
            try:
                street_address = user_data['fbfStreetAddress']
                if 'lgh' in street_address:
                    street_address_list = street_address.split()
                    number = street_address_list[street_address_list.index('lgh')]
                    floor = number.strip()[1]
                else:
                    floor = None
            except:
                floor = None

            # get name
            try:
                first_name = user_data.get('firstNames')
                middle_name = user_data.get('middleNames')
                last_name = user_data.get('lastNames')

                name = first_name or ''
                if middle_name:
                    name += f' {middle_name}'
                if last_name:
                    name += f' {last_name}'
            except:
                name = ''

            # get area
            try:
                area = user_data['housingInfo']['area']
            except:
                area = None
        except:
            return None


def filter_results(self):
    """
    if area data present in faktakontroll result then check otherwise ignore result
    if floor data present in faktakontroll result then check otherwise ignore result
    """
    pass


class Hemnet:
    def __init__(self, keyword):
        self.keyword = keyword
        self.location_id = None
        self.results = {}
        self.new_results = 0
        self.old_results = 0

    def search_keyword(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': '',
            'DNT': '1',
            'User-Agent': USER_AGENT,
            'X-Requested-With': 'XMLHttpRequest',
        }

        response = requests.get(f'https://www.hemnet.se/locations/show?q={self.keyword}',
                                headers=headers)
        try:
            data = response.json()[0]
            print(f'search result: {data["name"]}, location id: {data["id"]}')
            return data['id']
        except Exception as e:
            print(e)
            return None

    def search(self, page_number=1):
        if not self.location_id:
            self.location_id = self.search_keyword()
            self.load_results()

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
        soup = BeautifulSoup(res.content, 'html.parser')

        # list all the search results in current page
        lis = soup.find_all('li', {'class': 'normal-results__hit js-normal-list-item'})

        if len(lis) == 0:
            return False

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
                            try:
                                floor = re.findall(r'\d', flr.lower().rpartition('tr')[0])[-1]
                            except:
                                pass
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

                # check if the result was found before, ignore the result if true
                # otherwise, add it to the results dictionary
                if result_id not in self.results:
                    self.results.update({result_id: {
                        'address': address,
                        'city': city,
                        'area': self.parse_area(area),
                        'floor': floor,
                        'complete': False
                    }})
                    self.new_results += 1
                else:
                    self.old_results += 1
            except Exception as e:
                # print(e)
                # if any required data isn't present for a result then it will be skipped
                pass
        self.save_results()
        return True

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

        return float(area_string)

    def save_results(self):
        # create the cache folder if it doesn't exist
        os.makedirs(os.path.join(BASE_DIR, 'cache'), exist_ok=True)

        with open(os.path.join(BASE_DIR, 'cache', f'{self.location_id}.json'), 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

    def load_results(self):
        old_result_path = os.path.join(BASE_DIR, 'cache', f'{self.location_id}.json')
        if os.path.exists(old_result_path):
            with open(old_result_path, encoding='utf-8') as f:
                self.results = json.load(f)


if __name__ == '__main__':
    search_keyword = input('search: ')
    skip_hemnet = input('skip hemnet search? [y/n]: ').lower() == 'y'

    hemnet = Hemnet(search_keyword)

    # search the location on hemnet
    if skip_hemnet:
        print('loading saved hemnet data...')
        hemnet.location_id = hemnet.search_keyword()
        hemnet.load_results()
        print(f'{len(hemnet.results)} results found.')
    else:
        print('searching hemnet...')
        page_number = 1
        while True:
            # search for the keyword and keep vising
            # next pages until no more results are found
            results_found = hemnet.search(page_number=page_number)

            if not results_found:
                break
            print(f'page {page_number}: total {hemnet.new_results + hemnet.old_results} '
                  f'results found. {hemnet.new_results} new.')
            page_number += 1
    hemnet_search_results = hemnet.results

    # search the results from hemnet on faktakontroll
    # faktakontroll = Faktakontroll()
    # faktakontroll.refresh_tokens()
    # for result in hemnet_search_results:
    #     pass
