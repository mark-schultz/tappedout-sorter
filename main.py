import requests
import json
import time
import tqdm
import pprint
import datetime
from beautifultable import BeautifulTable

SCRYFALL_URL_PARTS = ["https://api.scryfall.com/cards/search?q=++!\"","\"&order=usd"]
TAPPEDOUT_URL = "http://tappedout.net/mtg-decks/dralnu-combocontrol-2/?fmt=txt"
RATE_LIMIT = .05
DEFAUlT_PRICE = 1000
MAX_AGE = 3
CACHE = 'cache.txt'


def get_tappedout_txt(link):
    """
    Downloads a .txt file from a (public) tappedout url, and formats
    the cards as a list of dicts.

    Specifically, {'Name':X,'Quantity':Y}

    The fields ['usd'] and ['Date'] will be added later in the protocol.
    """
    obj = requests.get(link + "?fmt=txt")
    if obj.status_code != 200:
        raise ImportError("The given link seems bad.  Is your deck private?")
    else:
        to_parse = obj.text
        lines = to_parse.split("\n")
        lines = [elem.strip("\n\r") for elem in lines if elem.strip("\n\r")]
        lines = [elem.split(" ", 1) for elem in lines]
        lines = [{"Name": elem[1], "Quantity":elem[0]} for elem in lines]

        return lines


def serialize_date():
    """
    Write the current date as MM/DD/YYYY, as the datetime object isn't serializable.
    """
    curr_date = datetime.datetime.now().date()
    return '{}/{}/{}'.format(curr_date.month, curr_date.day, curr_date.year)


def card_to_string(dct):
    """
    Adds the current date to a card object, then serializes the card.
    """
    dct['Date'] = serialize_date()
    return json.dumps(dct)


def string_to_card(string):
    return json.loads(string)


def read_cache():
    """
    Reads the entire cache, and returns the cards that have new enough prices to use.

    Based on parem MAX_AGE
    """
    try:
        with open(CACHE, 'r') as f:
            data = f.readlines()[0]
            jsonlist = data.replace("}{", "};{").split(';')
            cardslist = [string_to_card(line) for line in jsonlist]
            fresh_cards = [card for card in cardslist if age(card) <= MAX_AGE]
            return fresh_cards
    except (FileNotFoundError, IndexError):
        with open(CACHE, 'w') as f:
            f.write('')
        return []


def update_cache(ls):
    """
    Reads cache line by line, and replaces old values
    """
    if ls == [] or ls is None:
        raise ValueError("Can't update the Cache with an empty decklist")
    else:
        try:
            with open(CACHE, 'r') as f:
                scached_cards = f.readlines()[0]
                jsonlist = scached_cards.replace("}{", "};{").split(';')
                cached_cards = [string_to_card(line) for line in jsonlist]
        except IndexError:
            cached_cards = []
        for card in ls:
            scard = card_to_string(card)
            updated = False
            for old_card in cached_cards:
                if card['Name'] == old_card['Name']:
                    old_card = card
                    updated = True
                    break
            if not updated:
                cached_cards.append(card)
        scached_cards = [card_to_string(card) for card in cached_cards]
        with open(CACHE, 'w') as f:
            f.writelines(scached_cards)


def age(card):
    """
    Returns the last time the cache (of a particular card) was updated in days.
    """
    card_date = list(map(int, card['Date'].split('/')))
    delta = datetime.datetime.now().date() - \
        datetime.date(card_date[2], card_date[0], card_date[1])
    return delta.days


def find_card_price(dct, iterator=None):
    name = dct['Name']
    query = SCRYFALL_URL_PARTS[0] + name.replace(" ", "+").lower() + SCRYFALL_URL_PARTS[1]
    data = requests.get(query).json()['data'][0]
    try:
        return float(data['usd'])
    except KeyError:
        if iterator is None:
            pass
        else:
            iterator.write(
                "No USD for card {}, setting to {}".format(name, DEFAUlT_PRICE))
        return DEFAUlT_PRICE


def get_prices(ls):
    """
    Takes as input a list of cards to query, and queries them all
    while respecting the RATE_LIMIT for the API.
    """
    if ls == []:
        pass
    else:
        iterator = tqdm.tqdm(ls)
        for dct in iterator:
            start_time = time.time()
            price = find_card_price(dct, iterator)
            time_passed = time.time() - start_time
            wait_atleast = max(RATE_LIMIT - time_passed, 0)
            dct["Price"] = price
            dct['Date'] = serialize_date()
            time.sleep(wait_atleast)
    return ls


def make_table(sorted_ls):
    table = BeautifulTable()
    table.column_headers = ["Name", "Quantity", "Ind. Price",
                            "Total Price", "Cum. Cards", "Cum. Price"]
    cum_price = 0
    cum_cards = 0
    for card in sorted_ls:
        quantity = int(card['Quantity'])
        cum_cards += quantity
        total_price = quantity * card['Price']
        cum_price += total_price
        table.append_row([card['Name'], card['Quantity'], card[
                         'Price'], total_price, cum_cards, cum_price])
    return table

link = "http://tappedout.net/mtg-decks/02-05-17-GDa-the-gitrog-monster/"
link2 = "http://tappedout.net/mtg-decks/dralnu-combocontrol-2/"

def main(link):
    cardslist = get_tappedout_txt(link)
    card_names = [card['Name'] for card in cardslist]
    cache = read_cache()
    cached_cards = [card['Name'] for card in cache]
    cards_to_query = [card for card in cardslist if card[
        'Name'] not in cached_cards]
    new_cards = get_prices(cards_to_query)
    allcards = cache + new_cards
    update_cache(allcards)
    decklist = [card for card in allcards if card['Name'] in card_names]
    decklist.sort(key=lambda x: x['Price'])
    table = make_table(decklist)
    print(table)
