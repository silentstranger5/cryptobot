import requests

import bot

def make_request(params):
    headers = { 'X-CMC_PRO_API_KEY': bot.API_KEY }
    response = requests.get(bot.API_URL, params=params, headers=headers)
    data = response.json()
    return data


def extract_value(data, keys):
    value = data.get("data")
    if not value:
        return None

    for key in keys:
        if value and isinstance(value, list):
            value = value.pop(0)
        if value and all(x.isdigit() for x in list(value.keys())[:10]):
            value = list(value.values()).pop(0)
        value = value.get(key)
        if not value:
            return None
    return value


def get_name(symbol):
    params = dict(symbol=symbol)
    data = make_request(params)
    name = extract_value(data, (symbol, "name"))
    return name


def get_symbol(name):
    params = dict(slug=name)
    data = make_request(params)
    symbol = extract_value(data, ("symbol",))
    return symbol


def get_price(symbol: str):
    params = dict(symbol=symbol)
    data = make_request(params)
    price = extract_value(data, (symbol, "quote", "USD", "price"))
    return price

