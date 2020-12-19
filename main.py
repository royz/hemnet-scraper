import re
import requests
import time
import json
import os
from bs4 import BeautifulSoup
import openpyxl
from pprint import pprint
from string import ascii_uppercase
from openpyxl.styles import PatternFill

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
        except StopIteration as e:
            print(f'error while refreshing tokens: {e}')

    def search(self, hemnet_result, index=0, total=0):
        search_address = f'{hemnet_result["address"]}, {hemnet_result["city"]}'
        print(
            f'[{index} / {total}] {search_address} [area: {hemnet_result["area"]}]', end=': ')
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
            "searchString": search_address,
            "filterType": "p",
            "subscriptionRefNo": "20.750.025.01"
        }

        response = requests.post('https://www.faktakontroll.se/app/api/search',
                                 headers=headers, cookies=cookies, json=data)
        # refresh the tokens when their validity expires
        if response.status_code != 200:
            print('faktakontroll token expired. refreshing token...')
            self.refresh_tokens()
            return self.search(hemnet_result)

        data = response.json()
        results = data['hits']
        individual_results = [result['individual']
                              for result in results if result.get('individual')]
        # print(f'{len(individual_results)} results found')

        matches = []
        no_matches = []
        for result in individual_results:
            is_match = True

            # get floor number
            street_address = result['fbfStreetAddress']

            if 'lgh' in street_address:
                staddr = street_address[street_address.index('lgh'):]
                floor = int(re.findall(r'\d', staddr)[1])
                try:
                    apartment = re.findall(r'\d{4}', staddr)[0]
                except:
                    apartment = None
            else:
                floor = None
                apartment = None

            # get name
            try:
                first_name = result.get('firstNames')
                middle_name = result.get('middleNames')
                last_name = result.get('lastNames')

                name = first_name or ''
                if middle_name:
                    name += f' {middle_name}'
                if last_name:
                    name += f' {last_name}'
            except:
                name = ''

            # get area
            try:
                area = result['housingInfo']['area']
            except:
                area = None

            # check if the data matches with hemnet data
            potential_match = {'full_match': True}

            try:
                if hemnet_result['area'] == area:
                    pass
                elif area - 1 < hemnet_result['area'] < area + 1:
                    potential_match['full_match'] = False
                else:
                    is_match = False
            except:
                is_match = False

            # if (hemnet_result['floor'] and not floor) or (not hemnet_result['floor'] and floor):
            #     is_match = False
            if (hemnet_result['floor'] is None and floor == 0) or (hemnet_result['floor'] == 0 and floor is None):
                is_match = False

            elif hemnet_result['floor'] and floor:
                # if both hemnet and faktakontroll have floor info then check if they match
                if hemnet_result['floor'] == floor:
                    pass
                else:
                    # if the floors don't match, then don't include them as a match
                    is_match = False

            # if area and floor data match for both sources, then add name and phone number
            potential_match['name'] = name
            potential_match['floor'] = floor
            potential_match['apartment'] = apartment
            potential_match['street_address'] = street_address

            # try to fetch the phone number if available
            if is_match:
                potential_match['phone'] = self.get_phone_number(result['id'])
                matches.append(potential_match)
            else:
                no_matches.append(potential_match)
                pass
        print(f'{len(results)} results found, {len(matches)} matches')
        hemnet_result.update({'matches': matches, 'complete': True})
        return hemnet_result

    def get_phone_number(self, result_id):
        # print('getting phone number')
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
            phone_number_list = response.json()['individual']['phoneNumbers']
            return [phone_number['phoneNumber'] for phone_number in phone_number_list]
        except:
            return []


class Hemnet:
    def __init__(self, keyword):
        self.keyword = keyword
        self.location_id = None
        self.location_name = None
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
            self.location_name = data["name"]
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
            'new_construction': 'exclude'
        }

        res = requests.get('https://www.hemnet.se/bostader',
                           headers=headers, params=params)
        # with open('hem.html', 'w', encoding='utf-8') as f:
        #     f.write(res.text)
        #     quit()

        soup = BeautifulSoup(res.content, 'html.parser')

        # list all the search results in current page
        lis = soup.find_all(
            'li', {'class': 'normal-results__hit js-normal-list-item'})
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
                                floor = int(re.findall(
                                    r'\d', flr.lower().rpartition('tr')[0])[-1])
                            except:
                                pass
                            break
                else:
                    address = address_and_floor.strip()
                    floor = None

                location = li.find(
                    'span', {'class': 'listing-card__location-name'}).text.strip()
                city = location.split(',')[-1].strip()
                # get the area value if present
                attribs_div = li.find(
                    'div', {'class': 'listing-card__attributes-row'})
                attribs = attribs_div.find_all(
                    'div', {'class': 'listing-card__attribute'})

                area = None
                area_text = None
                extra_area = None
                for attrib in attribs:
                    if 'm²' in attrib.text:
                        area_text = attrib.text.strip()
                        area = attrib.text.strip().removesuffix('m²').strip()
                result_id = json.loads(li['data-gtm-item-info'])['id']

                # check if the result was found before, ignore the result if true
                # otherwise, add it to the results dictionary
                if result_id not in self.results:
                    self.results.update({result_id: {
                        'address_and_floor': address_and_floor,
                        'location': location,
                        'address': address,
                        'city': city,
                        'area': self.parse_area(area)[0],
                        'extra_area': self.parse_area(area)[1],
                        'area_text': area_text,
                        'floor': floor,
                        'complete': False,
                        'sold': False
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

        area_strings = area_string.split('+')
        area = float(area_strings[0].strip())
        if len(area_strings) > 1:
            extra_area = float(area_strings[1].strip())
        else:
            extra_area = None
        return area, extra_area

    def save_results(self):
        # create the cache folder if it doesn't exist
        os.makedirs(os.path.join(BASE_DIR, 'cache'), exist_ok=True)

        with open(os.path.join(BASE_DIR, 'cache', f'{self.location_id}.json'), 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

    def load_results(self):
        old_result_path = os.path.join(
            BASE_DIR, 'cache', f'{self.location_id}.json')
        if os.path.exists(old_result_path):
            with open(old_result_path, encoding='utf-8') as f:
                self.results = json.load(f)


def save_cache(data):
    with open(os.path.join(BASE_DIR, 'cache', f'{hemnet.location_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def save_xlsx(json_data, location, search_id):
    print('saving data...')
    headers = ['Id', 'Tot Hits', 'Tot Apartments', 'Address', 'City', 'Area', 'Extra Area',
               'Floor', 'Name', 'Phone', 'Apartment', 'Type', 'Sold']

    data = []
    for match_id, entry in json_data.items():
        if not entry['complete'] or entry['matches'] == []:
            continue
        address = entry['address'] or ''
        city = entry['city'] or ''
        area = entry['area'] or ''
        extra_area = entry['extra_area'] or ''
        floor = entry['floor'] or ''
        total_matches = len(entry['matches'])
        apartments = []
        row_template = [match_id, total_matches, 0, address, city, area, extra_area, floor]

        new_rows = []
        for match in entry['matches']:
            new_row = row_template.copy()
            apartment = match['apartment'] or ''
            if match['apartment'] and match['apartment'] in apartments:
                pass
            else:
                apartments.append(match['apartment'])

            new_row += [
                match['name'],
                '; '.join(match['phone']),
                f'lgh {apartment}' if apartment else '',
                'Full' if match['full_match'] else 'Partial',
                entry['sold']
            ]
            new_rows.append(new_row)

            # check if apartment is empty then number of apartments would be 0
            for row in new_rows:
                if row[len(row_template) + 2].strip() == '':
                    row[2] = 1
                else:
                    row[2] = len(apartments)

        if len(new_rows) <= 8:
            data.extend(new_rows)

    # create the excel workbook
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(headers)
    for row in data:
        sheet.append(row)

    # save the workbook
    try:
        filename = os.path.join(BASE_DIR, f'{location}.xlsx')
        wb.save(filename)
        print(f'data saved as "{filename}"')
    except:
        filename = os.path.join(BASE_DIR, f'{search_id}.xlsx')
        wb.save(filename)
        print(f'data saved as "{filename}"')


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

    # search the results from hemnet on faktakontroll
    print('\n\n')
    print(' searching faktakontroll '.center(100, '*'))
    faktakontroll = Faktakontroll()
    faktakontroll.refresh_tokens()
    index = 1
    total = len(hemnet.results)
    for result_id, result in hemnet.results.items():
        if result['complete']:
            pass
        else:
            faktakontroll_data = faktakontroll.search(result, index, total)
            hemnet.results[result_id].update(faktakontroll_data)
            save_cache(hemnet.results)
        index += 1
    save_xlsx(hemnet.results, hemnet.location_name, hemnet.location_id)
