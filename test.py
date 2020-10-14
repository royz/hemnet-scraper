import requests
from bs4 import BeautifulSoup

headers = {
    'authority': 'www.hemnet.se',
    'upgrade-insecure-requests': '1',
    'dnt': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-user': '?1',
    'sec-fetch-dest': 'document',
    'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'cookie': '__cfduid=d8a35d227c7e6e0b353f53d2802e399a41602081785; hn_exp_kpis=269; hn_exp_eca=851; hn_exp_sln=337; hn_exp_slo=1; ext_name=ojplmecpdpgccookcobabopnaifgidhf; _hemnet_listing_result_settings_list=normal; ___lpUId=0b676230-0360-41c3-8697-4b4badf055d4; hn_exp_opth=746; ___lpEU=true; _hemnet_listing_result_settings_preferred_sorting=true; _hemnet_listing_result_settings_sorting=creation+desc; _hemnet_session_id=6uk%2By%2B5yAJ8UadfFlBmkaGTcPjc4imPimEJ2V%2Folkop06hxjeqJiyNLR9q7b2AdTjblnmBEEgSCZ3ec9xwBlF%2FbUAfBFralA0pdFQNaCfwOPQa4VqLNRxFZfonIJFv98XgoTbWAM%2FwvWrbtQVXYa%2F833qweb9mcwhHFVcWfPJfknTQ%3D%3D--ubgy2j2Ppv94neh7--DrgIy49RdniQilW2kDv9Xw%3D%3D',
}

params = (
    ('location_ids[]', '17744'),
    ('item_types[]', ['villa', 'radhus', 'bostadsratt']),
)

response = requests.get('https://www.hemnet.se/bostader', headers=headers, params=params)

# NB. Original query string below. It seems impossible to parse and
# reproduce query strings 100% accurately so the one below is given
# in case the reproduced version is not "correct".
# response = requests.get('https://www.hemnet.se/bostader?location_ids%5B%5D=17744&item_types%5B%5D=villa&item_types%5B%5D=radhus&item_types%5B%5D=bostadsratt', headers=headers)


soup = BeautifulSoup(response.content, 'html.parser')
lis = soup.find_all('li', {'class': 'normal-results__hit js-normal-list-item'})
address = lis[0].find('h2', {'class': 'listing-card__street-address qa-listing-title'})
print('address:', address.text.strip())
location = lis[0].fins('span', {'class': 'listing-card__location-name'})
print('location:', location.text.strip())
