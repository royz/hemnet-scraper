import re
from pprint import pprint

import requests
import time
import json
import os
from bs4 import BeautifulSoup
import openpyxl

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
            f'[{index} / {total}] {search_address} [area: {hemnet_result.get("area")}]', end=': ')
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

        # with open('fakta-search.json', 'w', encoding='utf-8') as f:
        #     json.dump(response.json(), f, indent=2)

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
                more_data = self.get_more_details(result['id'])

                # pprint(more_data)

                potential_match['phone'] = more_data['numbers']
                potential_match['age'] = more_data['age']
                potential_match['gender'] = more_data['gender']
                potential_match['personal_number'] = more_data['personal_number']
                matches.append(potential_match)
            else:
                no_matches.append(potential_match)
                pass
        print(f'{len(results)} results found, {len(matches)} matches')
        hemnet_result.update({'matches': matches, 'complete': True})
        return hemnet_result

    def get_more_details(self, result_id):
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

            # with open('fakta-deep-search.json', 'w', encoding='utf-8') as f:
            #     json.dump(response.json(), f, indent=2)

            data = response.json()['individual']

            try:
                phone_numbers = [phone_number['phoneNumber'] for phone_number in data['phoneNumbers']]
            except:
                phone_numbers = []

            return {
                'numbers': phone_numbers,
                'age': data.get('age'),
                'gender': data.get('gender'),
                'personal_number': data.get('personalNumber')
            }
        except:
            return {
                'numbers': [],
                'age': None,
                'gender': None,
                'personal_number': None
            }


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
            self.location_id = data["id"]
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
            url = li.find('a')['href']
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
                        area = attrib.text.strip()
                        if area.endswith('m²'):
                            area = area[:len('m²')].strip()
                result_id = json.loads(li['data-gtm-item-info'])['id']

                # check if the result was found before, ignore the result if true
                # otherwise, add it to the results dictionary
                if result_id not in self.results:
                    self.results.update({result_id: {
                        'address_and_floor': address_and_floor,
                        'url': url,
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
        area_string = area_string.strip()
        if area_string.endswith('m²'):
            area_string = area_string[:len('m²')].strip().replace(',', '.')
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

    @staticmethod
    def get_more_data(url):
        headers = {
            'authority': 'www.hemnet.se',
            'user-agent': USER_AGENT,
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
        }

        response = requests.get(url, headers=headers)
        # with open('resp.html', 'w', encoding='utf-8') as f:
        #     f.write(response.text)
        #     quit()

        # find publish date
        matches = re.findall(r'(?<="publication_date":")(.*?)(?=")', response.text)
        if matches:
            publication_date = matches[0]
        else:
            publication_date = None

        # find housing type
        matches = re.findall(r'(?<="housing_form":")(.*?)(?=")', response.text)
        if matches:
            housing_form = matches[0]
        else:
            housing_form = None

        return {
            'publication_date': publication_date,
            'housing_form': housing_form
        }

    def search_sold_properties(self):
        headers = {
            'authority': 'www.hemnet.se',
            'upgrade-insecure-requests': '1',
            'dnt': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,sv;q=0.6',
        }

        sold_properties = []

        for page_num in range(1, 51):
            print(f'page: {page_num}')
            params = {
                'housing_form_groups[]': ['houses', 'row_houses', 'apartments'],
                'location_ids[]': self.location_id,
                'page': page_num
            }

            response = requests.get('https://www.hemnet.se/salda/bostader', headers=headers, params=params)
            soup = BeautifulSoup(response.content, 'html.parser')
            links = soup.find_all('a', {'class': 'sold-property-listing'})
            for link in links:
                href = link['href']
                sold_properties.append(href)
        return sold_properties

    @staticmethod
    def get_sold_property_id(property_link):
        headers = {
            'authority': 'www.hemnet.se',
            'user-agent': USER_AGENT,
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
        }

        try:
            sold_date = 'sold but date not found'
            resp = requests.get(property_link, headers=headers)

            with open('hemnet-error.html', 'w', encoding='utf-8') as f:
                f.write(resp.text)

            datalayer_text = re.findall(r'(?<=dataLayer = )(.*)(?=;)', resp.text)[0]
            datalayer = json.loads(datalayer_text)
            for dl in datalayer:
                try:
                    if 'property' in dl.keys():
                        prop_id = dl['property']['id']
                    if 'sold_property' in dl.keys():
                        sold_date = dl['sold_property']['sold_at_date']
                except:
                    pass
            return prop_id, sold_date
        except StopIteration:
            return None, None


def get_date(dt):
    dt = str(dt)
    try:
        return re.findall(r'\d+-\d+-\d+', dt)[0]
    except:
        return ''


def save_cache(data):
    with open(os.path.join(BASE_DIR, 'cache', f'{hemnet.location_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def get_phone_columns(phone_numbers):
    if len(phone_numbers) > 6:
        phone_numbers = phone_numbers[:6]
    elif len(phone_numbers) < 6:
        phone_numbers += [''] * (6 - len(phone_numbers))
    return phone_numbers


def save_xlsx(json_data, location, search_id):
    print('saving data...')
    headers = ['Id', 'Tot Hits', 'Tot Apartments', 'Address', 'City', 'Bostadstyp', 'Area', 'Extra Area',
               'Floor', 'Name', 'Kön', 'Personnr', 'Ålder'] + [
                  'Phone 1', 'Phone 2', 'Phone 3', 'Phone 4', 'Phone 5', 'Phone 6',
              ] + ['Apartment', 'Type', 'Publish Date', 'Sold']

    data = []
    for match_id, entry in json_data.items():
        if not entry['complete'] or entry['matches'] == []:
            continue
        address = entry['address'] or ''
        city = entry['city'] or ''
        house_type = entry.get('house_type') or ''
        area = entry['area'] or ''
        extra_area = entry.get('extra_area') or ''
        floor = entry['floor'] or ''
        total_matches = len(entry['matches'])
        apartments = []
        sold = get_date(entry.get('sold'))
        row_template = [match_id, total_matches, 1, address, city, house_type, area, extra_area, floor]

        new_rows = []
        for match in entry['matches']:
            new_row = row_template.copy()
            apartment = match['apartment'] or ''
            if match['apartment'] and match['apartment'] in apartments:
                pass
            else:
                apartments.append(match['apartment'])

            new_row += [match['name'], match.get('gender') or '', match.get('personal_number') or '',
                        match.get('age') or '',
                        ] + get_phone_columns(match['phone']) + [
                           f'lgh {apartment}' if apartment else '',
                           'Full' if match[
                               'full_match'] else 'Partial',
                           get_date(entry['publish_date']),
                           sold
                       ]
            new_rows.append(new_row)

            # check if apartment is empty then number of apartments would be 1
            for row in new_rows:
                if row[len(row_template) + 10].strip() == '':
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

    # freeze the header
    sheet.freeze_panes = 'A2'

    # add filters to all columns
    sheet.auto_filter.ref = sheet.dimensions

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

    print('choose an option:', '1. new', '2. sold', sep='\n')
    new_or_sold = input('option: ').strip()
    if new_or_sold == '2':
        hemnet = Hemnet(search_keyword)
        search_id = hemnet.search_keyword()

        if not os.path.exists(os.path.join(BASE_DIR, 'cache', f'{search_id}.json')):
            print(f'search cache not found for {hemnet.location_name}')
            quit()
        else:
            hemnet.load_results()
            print('getting list of sold properties...')

            sold_properties_links = hemnet.search_sold_properties()

            # with open('sold-properties_links.json', 'r', encoding='utf-8') as f:
            #     sold_properties_links = json.load(f)

            # with open('sold-properties_links.json', 'w', encoding='utf-8') as f:
            #     json.dump(sold_properties_links, f, indent=2)

            print(len(sold_properties_links), 'sold properties found')

            sold_properties = {}
            for i, sold_prop_link in enumerate(sold_properties_links):
                print(f'getting sold date for ({i + 1}/{len(sold_properties_links)}):', end=' ')
                prop_id, sold_date = hemnet.get_sold_property_id(sold_prop_link)
                print(prop_id, f'({sold_date})')
                sold_properties[prop_id] = sold_date

            with open('sold-property-ids.json', 'w', encoding='utf-8') as f:
                json.dump(sold_properties, f, indent=2)

            for property_id in hemnet.results.keys():
                if int(property_id) in sold_properties.keys():
                    hemnet.results[property_id]['sold'] = sold_properties[int(property_id)]

            hemnet.save_results()
            save_xlsx(hemnet.results, hemnet.location_name, hemnet.location_id)
        quit()

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

    # get the publish date for the new results from hemnet
    print('getting publish date and housing type for hemnet search results...')
    for result_id, result in hemnet.results.items():
        if result.get('publish_date'):
            print(f"{result_id}: {result['publish_date']}")
        else:
            result_url = result.get('url')
            if result_url:
                more_details = hemnet.get_more_data(result_url)
                pub_date = more_details['publication_date']
                house_type = more_details['housing_form']
                print(f"{result_id} ({house_type}): {pub_date}")
            else:
                pub_date = ''
                house_type = ''
                print(f"{result_id}: url not found")
            hemnet.results[result_id]['publish_date'] = pub_date
            hemnet.results[result_id]['house_type'] = house_type
    hemnet.save_results()

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