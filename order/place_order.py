import requests
import hmac
import hashlib
from urllib.parse import urlencode 
from configs.binance_config import *
from configs.account_info import *

import os 



api_key = os.environ['API_KEY']
secret_key = os.environ['SECRET_KEY']

order_endpoint = 'https://fapi.binance.com/fapi/v1/order'

def place_order(symbol, side, leverage):
    symbol = f'{symbol.upper()}'  # Ensure correct symbol format
    current_price = get_current_price(symbol)
    if current_price is None: 
        print(f"Failed to retrieve current price for {symbol}.")
        return

    try:
        account_info = get_account_info(api_key, secret_key)
        if account_info:
            usdt_balance = 0
            for asset in account_info['assets']:
                if asset['asset'] == 'USDT':
                    usdt_balance = float(asset['availableBalance'])
                    break
            print(f"USDT Balance: {usdt_balance}")

            if usdt_balance == 0:
                print("Insufficient USDT balance.")
                return

            # Calculate the quantity based on balance, leverage, and current price
            quantity = (usdt_balance*0.35 * leverage) / current_price
            print(f"Quantity before rounding: {quantity}")
            # Get the quantity precision from the LOT_SIZE filter
            quantity_precision = get_quantity_precision(symbol)
            if quantity_precision is not None:
                quantity = round(quantity, quantity_precision)
                print(f"Quantity after rounding: {quantity}")

            if quantity == 0:
                print("Calculated quantity is zero. Check balance and leverage.")
                return

            payload = {
                'symbol': symbol,
                'side': side.upper(),
                'type': 'LIMIT',
                'price': current_price,
                'quantity': quantity,
                'timestamp': get_server_time(),
                'recvWindow': 50000,
                'timeInForce': 'GTC',
            }
            query_string = '&'.join([f"{k}={v}" for k, v in payload.items()])
            signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
            payload['signature'] = signature

            headers = {'X-MBX-APIKEY': api_key}
            response = requests.post(order_endpoint, params=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                print("Order successfully placed:")
                print(data)
            else:
                print(f"Failed to place order. Status code: {response.status_code}, Message: {response.text}")
        else:
            print("Failed to get account information.")
    except Exception as e:
        print(f"An error occurred: {e}")