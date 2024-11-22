
import requests
import time
import hmac
import hashlib
import math
from urllib.parse import urlencode

account_endpoint = 'https://fapi.binance.com/fapi/v2/account'
exchange_info_endpoint = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
def get_server_time():
    url = 'https://fapi.binance.com/fapi/v1/time'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['serverTime']
    else:
        return int(time.time() * 1000)  # Fallback to local time


def get_current_price(symbol):
    url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol.upper()}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            price = float(data['price'])
            return price
        else:
            print(f"Failed to retrieve current price for {symbol}. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching current price for {symbol}: {e}")
        return None

def get_account_info(api_key, secret_key):
    try:
        timestamp = get_server_time()
        payload = {'timestamp': timestamp}
        query_string = urlencode(payload)
        signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        payload['signature'] = signature
        headers = {'X-MBX-APIKEY': api_key}
        response = requests.get(account_endpoint, params=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"Failed to get account information. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
# Function to get the tick size for a symbol
def get_tick_size(symbol):
    try:
        response = requests.get(exchange_info_endpoint)
        if response.status_code == 200:
            data = response.json()
            for symbol_info in data['symbols']:
                if symbol_info['symbol'] == symbol.upper():
                    filters = symbol_info.get('filters', [])
                    for filter_item in filters:
                        if filter_item['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter_item['tickSize'])
                            return tick_size
                    print(f"Tick size not found for symbol {symbol}.")
                    return None
            print(f"Symbol {symbol} not found in exchange info.")
            return None
        else:
            print(f"Failed to get exchange info. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def calculate_precision(symbol):
    tick_size = get_tick_size(symbol)
    if tick_size is not None:
        precision = -int(math.log10(tick_size))
        return precision
    else:
        return None
    
def get_max_quantity(symbol):
    try:
        response = requests.get(exchange_info_endpoint)
        if response.status_code == 200:
            data = response.json()
            for symbol_info in data['symbols']:
                if symbol_info['symbol'] == symbol.upper():
                    for filter_item in symbol_info['filters']:
                        if filter_item['filterType'] == 'LOT_SIZE':
                            return float(filter_item['maxQty'])
            print(f"Max quantity not found for symbol {symbol}.")
            return float('inf')  # Return a large number if not found
        else:
            print(f"Failed to get exchange info. Status code: {response.status_code}, Message: {response.text}")
            return float('inf')
    except Exception as e:
        print(f"An error occurred: {e}")
        return float('inf')

def get_quantity_precision(symbol):
    try:
        response = requests.get(exchange_info_endpoint)
        if response.status_code == 200:
            data = response.json()
            for symbol_info in data['symbols']:
                if symbol_info['symbol'] == symbol.upper() :
                    precision = symbol_info.get('quantityPrecision', None)
                    if precision is not None:
                        return precision
                    else:
                        print(f"Quantity precision not found for symbol {symbol}.")
                        return None
            print(f"Symbol {symbol} not found in exchange info.")
            return None
        else:
            print(f"Failed to get exchange info. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None