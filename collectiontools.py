import config
import requests
import logging
import datetime
import jsonpickle
import json

logging.basicConfig(filename='example.log', level=logging.DEBUG)


class Card:
    def __init__(self, name, mset=None):
        """
        Queries a card (given a name and set), and sets all of it's attributes based on
        Scryfall's returned JSON
        """
        if (name in [key[0] for key in cached_cards.cards] and mset is None) or ((name, mset) in [key for key in cached_cards.cards]):
            if mset is None:
                keys = cached_cards.cards.keys()
                right_key = [key for key in keys if key[0] == name]
                self = cached_cards.cards[right_key[0]]
            else:
                self = cached_cards.cards[(name, mset)]
            if self.get_price_age() > config.MAX_AGE:
                self.update_price()
        else:
            self.name = name
            self.set = mset
            self.data = self.query_scryfall(mset)
            for key in self.data:
                setattr(self, key, self.data[key])
            self.access_date = datetime.datetime.now().date()
            self.update_cache()

    def __str__(self):
        outstr = ""
        outstr += self.name + " - " + self.mana_cost + "\n"
        outstr += self.type_line + "\n"
        outstr += self.oracle_text + "\n"
        outstr += self.set
        return outstr

    def __repr__(self):
        return "{} ({})".format(self.name, self.set)

    def query_scryfall(self, mset):
        """
        Queries Scryfall on the card's name, and returns the JSON associated with it.
        """
        if mset is None:
            logging.info('Querying Scryfall on {}...'.format(self.name))
            query = config.SCRYFALL_CHEAPEST_PARTS[0] + self.name.replace(
                " ", "+").lower() + config.SCRYFALL_CHEAPEST_PARTS[1]
            return requests.get(query).json()['data'][0]
        else:
            # TODO: Make card + set query
            raise NotImplementedError
            logging.info(
                'Querying Scryfall on {} - {}...'.format(self.name, mset))
            query = config.SCRYFALL_CHEAPEST_PARTS[0] + self.name.replace(
                " ", "+").lower() + config.SCRYFALL_CHEAPEST_PARTS[1]
            return requests.get(query).json()['data'][0]

    def get_price(self, currency='usd'):
        logging.info('Finding price of {} in {}...'.format(
            self.name, currency))
        if self.get_price_age() <= config.MAX_AGE:
            price = getattr(self, currency)
            logging.info('Price of {} is recent'.format(price))
            return price
        else:
            logging.info('No recent price found.')
            self.update_price()
            return getattr(self, currency)

    def update_price(self):
        logging.info('Updating price of {}...'.format(self.name))
        data = self.query_scryfall()
        try:
            for key in ['usd', 'eur', 'tix']:
                logging.info('{} price of {} found.'.format(key, price))
                setattr(self, key, data[key])
            self.access_date = datetime.datetime.now().date()
        except KeyError as e:
            message = 'Price not found on Scryfall:\nQuery:{}\nJSON:{}'.format(
                query, data)
            logging.critical(message)
            print(message)
            raise e

    def get_price_age(self):
        """
        Returns the last time the price of a particular card was retrieved.
        Returns +infinity if the price hasn't been retrieved.
        """
        if self.price_access_date is None:
            return float('inf')
        else:
            delta = datetime.datetime.now().date() - self.price_access_date
            return delta.days



class Collection:
    def __init__(self, name):
        self.name = name
        self.cards = {}

    def search_card(self, card):
        logging.info('Looking for card {}...'.format(card.name))
        for key in cards:
            idx_name, idx_set = key[0], key[1]
            if idx_name == card.name and idx_set == card.set:
                logging.info('Found card {} from {}.'.format(
                    card.name, card.set))
                return self.cards[(idx_name, idx_set)][0]
            else:
                logging.info('Could not find card.')
                return None

    def length(self):
        return sum(self.cards[key][1] for key in self.cards)

    def total_price(self, currency='usd'):
        logging.info('Calculating total price for {}...'.format(self.name))
        total = sum(key[1] * float(getattr(key[0], currency))
                    for key in self.cards)
        logging.info('Computed total: {}'.format(total))
        return total

    def add_card(self, card):
        logging.info(
            'Adding card {} - {} to {}...'.format(card.name, card.set, self.name))
        if (card.name, card.set) in self.cards:
            self.cards[(card.name, card.set)] = [
                card, self.cards[(card.name, card.set)][1] + 1]
            logging.info('Card found in collection.  There are {} copies now.'.format(
                self.cards[(card.name, card.set)]))
        else:
            logging.info('Card not found in collection.  There is 1 copy now.')
            self.cards[(card.name, card.set)] = [card, 1]

    def remove_card(self, card):
        logging.info('Removing {} from collection {}...'.format(
            card.name, self.name))
        if (card.name, card.set) in self.cards:
            quantity = self.cards[(card.name, card.set)]
            self.cards[(card.name, card.set)] = [card, quantity - 1]
            if quantity - 1 == 0:
                logging.info(
                    'Card removed.  There are no copies left in this collection.')
                self.cards.pop((card.name, card.set))
                return True
            else:
                logging.info(
                    'Card removed.  There are {} copies left in this collection.'.format(quantity - 1))
                return True
        else:
            logging.info('Card not found in collection.')
            return False


def import_tappedout(link, collection):
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
        lines = [elem.strip("\n\r").split(" ", 1)
                 for elem in lines if elem.strip("\n\r")]
        for elem in lines:
            Card(elem[1], collection, elem[0])
            names_list = [card.name]
        return lines


def read_cache():
    """
    Reads the cache, and returns a collection of cards in it.
    """
    cached_cards = Collection('cached_cards')
    try:
        with open(config.CACHE, 'r') as f:
            logging.info('Reading the cache...')
            for line in f.readlines():
                card = jsonpickle.decode(line.rstrip('\n'))
                logging.info('Read card: {} ({})'.format(card.name, card.set))
                cached_cards.add_card(card)
    except FileNotFoundError as e:
        logging.warning('{} not found.  Creating it now.'.format(config.CACHE))
        with open(config.CACHE, 'w') as f:
            f.write('')
    except json.decoder.JSONDecodeError as e:
        logging.warning('Cache corrupted, JSON could not be recovered.')
        raise e
    return cached_cards

def update_cache(collection):
    """
    Takes a collection, and updates the cache entry of each card in it.
    """
    with open(config.CACHE, 'r') as f:
        lines = f.readlines()
    header, body = lines[0], lines[1:]
    header.strip('\n')
    card_headers = ['[{}]'.format(key) for key in collection.cards]
    for card_header in card_headers:
        if card_header in header:
            raise NotImplementedError
    if card_header in header:
        raise NotImplementedError
    else:
        header = ";".join(header, card_header) + '\n'
        body.append(jsonpickle.encode(self) + '\n')
        with open(config.CACHE, 'w') as f:
            f.writelines([header] + body)



if __name__ == '__main__':
    cached_cards = read_cache()
