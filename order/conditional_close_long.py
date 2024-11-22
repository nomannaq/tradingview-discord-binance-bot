import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode 
from configs.binance_config import *
from configs.account_info import *

import os 

api_key = os.environ['API_KEY']
secret_key = os.environ['SECRET_KEY']

order_endpoint = 'https://fapi.binance.com/fapi/v1/order'
def close_long_position(symbol, close_quantity=None, max_attempts=20):  # 5 minutes max (20 * 15 seconds)
    for attempt in range(max_attempts):
        try:
            # Get account information and current price
            account_info = get_account_info(api_key, secret_key)
            current_price = get_current_price(f"{symbol.upper()}")
            
            if account_info:
                # Find open positions
                open_positions = [position for position in account_info['positions'] if float(position['positionAmt']) != 0]
                position_found = any(position['symbol'] == f"{symbol.upper()}" for position in open_positions)
                
                # Check if position is already closed
                if not position_found:
                    print(f"Position already closed for {symbol}")
                    return True
                
                for position in open_positions:
                    if position['symbol'] == f"{symbol.upper()}":
                        # Calculate quantity to close
                        total_quantity = abs(float(position['positionAmt']))
                        quantity = close_quantity if close_quantity is not None else total_quantity
                        timestamp = get_server_time()
                        
                        # Prepare order parameters
                        payload = {
                            'symbol': f'{symbol.upper()}',
                            'side': 'SELL',
                            'type': 'LIMIT',
                            'price': current_price,
                            'quantity': quantity,
                            'timestamp': timestamp,
                            'recvWindow': 50000,
                            'timeInForce': 'GTC'
                        }
                        
                        query_string = '&'.join([f"{k}={v}" for k, v in payload.items()])
                        signature = hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()
                        payload['signature'] = signature
                        headers = {'X-MBX-APIKEY': api_key}

                        # Check for and cancel open orders
                        open_orders = get_open_orders(api_key, secret_key, symbol)
                        if open_orders:
                            print(f"Attempt {attempt + 1}: Cancelling existing orders for {symbol}")
                            for order in open_orders:
                                delete_payload = {
                                    'symbol': f'{symbol.upper()}',
                                    'orderId': order['orderId'],
                                    'timestamp': timestamp,
                                    'recvWindow': 50000
                                }
                                delete_query_string = urlencode(delete_payload)
                                delete_signature = hmac.new(secret_key.encode(), delete_query_string.encode(), hashlib.sha256).hexdigest()
                                delete_payload['signature'] = delete_signature
                                delete_response = requests.delete(order_endpoint, params=delete_payload, headers=headers)
                                
                                if delete_response.status_code == 200:
                                    print(f"Order {order['orderId']} cancelled successfully.")
                                else:
                                    print(f"Failed to cancel order {order['orderId']}.")

                        # Place new closing order
                        response = requests.post(order_endpoint, params=payload, headers=headers)
                        
                        if response.status_code == 200:
                            print(f"Attempt {attempt + 1}: Order to close long position placed at price {current_price}")
                            time.sleep(10)  # Wait 15 seconds before checking again
                        else:
                            print(f"Failed to place order. Status code: {response.status_code}")
                            return False
                        
                        break
            else:
                print("Failed to get account information.")
                return False
                
        except Exception as e:
            print(f"Error in close_long_position: {str(e)}")
            return False
    
    print(f"Failed to close position after {max_attempts} attempts")
    return False
