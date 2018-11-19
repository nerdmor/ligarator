import re
import time
import requests
import json
from bs4 import BeautifulSoup
from os import system, name, sep
import sys
from ortools.linear_solver import pywraplp
from datetime import date


class Solver(pywraplp.Solver):
    '''Wrapper/overwrite of the Solver class to modifiy the IntVar class
    (which we cannot access as it is in a C compiled file ): ).
    Modifies the IntVar to accept name as either a tuple or string
    '''
    def IntVar(self, floo, cei, name):
        if type(name) == tuple:
            store_name = name[0]
            card_name = name[1]
            name = store_name[0:31] + '|' + card_name[0:32]
        else:
            tmp = name.split('|')
            store_name = tmp[0]
            if len(tmp) == 2:
                card_name = tmp[1]
            else:
                card_name = tmp[0]

        exit = super().IntVar(floo, cei, name)
        exit.store_name = store_name
        exit.card_name = card_name
        return exit


def clear_screen():
    '''Clears the console screen in a system-agnostic way
    '''
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


def sysexit():
    '''Demands a 'Press enter to exit' before sys.exit()
    '''
    input('Pressione enter para sair')
    sys.exit()


def make_request_liga(baseurl, cardname=None, cardid=None, page=1):
    '''Makes a request to Ligamagic, cleans and returns the HTML

    Args:
        baseurl(str): required
            The basic URL to be used in requests. It is not hardcoded to make
            it easier to change in case they change the consumable endpoint
        cardname(str): optional
            Either this or cardid must be set.
            The card name to be searched for. Must be in a way that Ligamagic
            can read/find
        cardid(str): optional
            Either this or cardname must be set.
            The id of the card being pulled. Useful when getting the second and
            later pages.
        page(int): optional
            Defaults to 1
            The page of results to be gotten.

    Returns:
        False
            When the response is not 200 or parsing fails
        str
            with the HTML returned by ligamagic
    '''

    if cardname is None and cardid is None:
        raise ValueError('cardname or cardid are mandatory')
    elif cardname is not None and cardid is not None:
        raise ValueError('can only use cardname or cardid, not both')

    if cardname is not None:
        cardid = ''
    else:
        cardname = ''

    params = {
        'card': cardname,
        'cardAux': None,
        'cardID': cardid,
        'category': '1',
        'exactMatch': '1',
        'orderBy': '1',
        'page': page,
        'unixt': int(time.time()),
    }
    r = requests.get(baseurl, params=params)
    if r.status_code != 200:
        return False
    else:
        return clean_liga_html(r.text)


def clean_liga_html(html):
    '''Cleans liga's HTML from some known problems

    Args:
        html(str): required
            the html to be cleaned

    Returns:
        str
            the given HTML cleaned
    '''

    replacements = {
        'id="mob-store" class="panel panel-card db-card-place"': 'class="mob-store"',  # noqa 502
        '\\\'': ''
    }

    for k, v in replacements.items():
        html = html.replace(k, v)

    return html


def parse_liga_offers(html, cardname):
    '''Parses the given HTML by Ligamagic and returns a list of dicts with the
    acquired data

    Args:
        html(str): required
            the HTML returned by ligamagic
        cardname(str): required
            the card's name, in a format that makes it findable in Liga

    Returns:
        (card_id, offers)
            card_id:
                False when there is no next page and thus the card's ID is not
                clear
                str with the card ID when there is a next page
            offers:
                False when the parsing fails
                list of dicts with the data when it succeeds.
                Returned dicts have the following format:
                {
                    'card': cardname,
                    'store': <STORE NAME FROM HTML>(str),
                    'quantity': <THE REPORTED STORE STOCK>(int),
                    'price': <THE REPORTED STORE PRICE>(float)
                }
    '''

    if html is False:
        return False, False

    soup = BeautifulSoup(html, 'html.parser')
    try:
        card_id = soup.find(class_='db-view-more').get('onclick')
        card_id = re.findall(
            'appScreen\\.cardOpenNextPage\\((\\d+)\\)', card_id)[0]
    except Exception as e:
        card_id = False

    re_storename = re.compile('advsearch\\.storeSearch\\("(.+)"\\)')
    re_quantity = re.compile('^(\\d+) unid[s\\.]')
    re_price = re.compile('^R\\$\\s+(\\d+),(\\d+)')
    offers = []

    for off in soup.find_all(class_='mob-store'):
        offer = {
            'card': cardname,
            'store': '',
            'quantity': 0,
            'price': 0.0
        }

        # Store name
        store_name = off.find(class_='store-picture')
        store_name = store_name.get('onclick')
        store_name = re_storename.findall(store_name)[0]
        offer['store'] = store_name

        # quantity
        quantity = off.find(class_='form-place').get_text().strip()
        quantity = int(re_quantity.findall(quantity)[0])
        offer['quantity'] = quantity

        # price
        try:
            price = off.find(class_='mob-preco-desconto')\
                .find('s').get_text().strip()
        except Exception as e:
            price = off.find(class_='store-card-price').get_text().strip()
        price = re_price.findall(price)[0]
        price = int(price[0]) + (int(price[1])/100)
        offer['price'] = price
        offers.append(offer)

    if len(offers) < 1:
        offers = False

    return card_id, offers


def get_liga_offers(baseurl, cardname):
    '''Gets all offers for a given cardname

    Args:
        baseurl(str): required
            The basic URL to be used in requests. It is not hardcoded to make it
            easier to change in case they change the consumable endpoint
        cardname(str): required
            The card name to be searched for. Must be in a way that Ligamagic
            can read/find

    Returns:
        False if anything fails (not pythonic. I know.)
        List of dicts from parse_liga_offers
    '''

    current_page = 1
    html = make_request_liga(baseurl, cardname=cardname)
    if html is not False:
        card_id, offerlist = parse_liga_offers(html, cardname)

    if offerlist is False:
        return False

    while card_id is not False:
        current_page += 1
        html = make_request_liga(
            baseurl, cardid=card_id, page=current_page)
        if html is False:
            break

        card_id, offers = parse_liga_offers(html, cardname)
        if offers:
            offerlist += offers

    return offerlist


def clean_store_offers(offers, banned_stores=[]):
    """TODO
    """

    clean_offers = []
    seen_offers = []
    for o in offers:
        if o['store'] in banned_stores:
            continue
        oname = o['store'] + o['card']
        if oname not in seen_offers:
            seen_offers.append(oname)
            clean_offers.append(o)
        else:
            for i in range(len(clean_offers)):
                if clean_offers[i]['store'] == o['store']\
                        and clean_offers[i]['card'] == o['card']:
                    clean_offers[i]['quantity'] += o['quantity']
                    if o['price'] > clean_offers[i]['price']:
                        clean_offers[i]['price'] = o['price']
    return clean_offers


def validate_offer_dic(offer, needed_fields):
    """TODO
    """
    if type(offer) is not dict:
        return False

    if needed_fields is not list:
        raise TypeError('needed_fields must be a list of str')

    for f in needed_fields:
        if f not in offer:
            return False
    return True


def load_offers_from_file(filename):
    """TODO
    """

    try:
        f = open(filename, 'r', encoding='utf-8')
    except Exception as e:
        return False

    jdata = json.load(f)
    needed_fields = ['card', 'store', 'quantity', 'price']
    exit = []
    for d in jdata:
        if 'date' in d:
            dl = d['date'].split('-')
            jdate = date(dl[0], dl[1], dl[2])
            if jdate < date.today():
                return False
        elif validate_offer_dic(d, needed_fields) is True:
            exit.append(d)

    if len(exit) > 1:
        return exit


def save_offers_to_file(offers, filename):
    """TODO
    """
    try:
        with open(filename, 'w+', encoding='utf-8') as f:
            offers = [{'date': date.today()}] + offers
            json.dump(offers, f)
            return True
    except Exception as e:
        return False


def make_filepaths(entry_path):
    """TODO
    """
    isep = sep
    pathlist = entry_path.split(isep)
    if len(pathlist) == 1:
        isep = '/'
        pathlist = entry_path.split(isep)
    filename = pathlist[-1]
    pathlist = pathlist[0:-1]

    exit = {
        'entry': sep.join((pathlist + [filename])),
        'buylist': sep.join((pathlist + ['buylist_' + filename])),
        'offers': sep.join((pathlist + ['offers_' + filename]))
    }

    return exit
