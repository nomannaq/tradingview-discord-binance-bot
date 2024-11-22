from configs.binance_config import *
import os 

api_key = os.environ['API_KEY']
secret_key = os.environ['SECRET_KEY']

def get_open_orders(api_key, secret_key, symbol):
    try:
        # Endpoint for retrieving open orders
        open_orders_endpoint = 'https://fapi.binance.com/fapi/v1/openOrders'
        # Timestamp for the request
        timestamp = get_server_time()
        # Construct the query parameters
        payload = {'symbol': f"{symbol.upper()}", 'timestamp': timestamp}
        query_string = urlencode(payload)
        # Generate the signature
        signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        # Add the signature to the payload
        payload['signature'] = signature
        # Add the API key to the headers
        headers = {'X-MBX-APIKEY': api_key}
        # Send the request to retrieve open orders
        response = requests.get(open_orders_endpoint, params=payload, headers=headers)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            orders = response.json()
            if not orders:
                print("No open orders found.")
            return orders
        elif response.status_code == 400:
            print(f"Failed to retrieve open orders. Invalid symbol: {symbol}")
            return None
        else:
            print(f"Failed to retrieve open orders. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        print(f"An error occurred while retrieving open orders: {e}")
        return None
    

def get_position_amount(api_key, secret_key, symbol):
    try:
        account_info = get_account_info(api_key, secret_key)
        if account_info:
            for position in account_info['positions']:
                if position['symbol'] == f"{symbol.upper()}":
                    return abs(float(position['positionAmt']))
            print(f"No position found for symbol {symbol}.")
        else:
            print("Failed to get account information.")
    except Exception as e:
        print(f"An error occurred while fetching position amount for {symbol}: {e}")
    return None
