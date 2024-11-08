import os
import discord as allert
import requests
import hashlib
import hmac
import time
from urllib.parse import urlencode
from discord.ext import commands

# Load environment variables 
DISCORD_BOT_TOKEN = 'your_discord_bot_token'  # Token for the Discord bot to interact with the Discord API
api_key = 'your_api_key'  # API key to authenticate with Binance
secret_key = 'your_secret_key'  # Secret key for signing requests to Binance
YOUR_CHANNEL_ID = 1234 # Replace with your actual channel ID where the bot will listen for messages
Server_Response_Channel_ID= 1234 # Replace with your actual channel ID where the bot will send responses
account_endpoint = 'https://fapi.binance.com/fapi/v2/account'
order_endpoint = 'https://fapi.binance.com/fapi/v1/order'
exchange_info_endpoint = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
intents = allert.Intents.all()
client = allert.Client(intents=intents)
leverage=10


def get_server_time():
    url = 'https://fapi.binance.com/fapi/v1/time'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['serverTime']
    else:
        return int(time.time() * 1000)  # Fallback to local time



#Function to get account info
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
                            time.sleep(15)  # Wait 15 seconds before checking again
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



def close_short_position(symbol, close_quantity=None, max_attempts=20):  # 5 minutes max (20 * 15 seconds)
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
                            'side': 'BUY',  # BUY to close a short position
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
                            print(f"Attempt {attempt + 1}: Order to close short position placed at price {current_price}")
                            time.sleep(15)  # Wait 15 seconds before checking again
                        else:
                            print(f"Failed to place order. Status code: {response.status_code}")
                            return False
                        
                        break
            else:
                print("Failed to get account information.")
                return False
                
        except Exception as e:
            print(f"Error in close_short_position: {str(e)}")
            return False
    
    print(f"Failed to close position after {max_attempts} attempts")
    return False


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
            quantity = (usdt_balance/6 * leverage) / current_price
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
#Function to get maximum quantity
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
# Function to get the quantity precision for a symbol
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

@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
@client.event
async def on_message(message):
    if message.channel.id == YOUR_CHANNEL_ID:
        # Use the message content as is for case-sensitive comparison
        message_content = message.content.strip()
        print(f"Received message: {message_content}")
        
        response_channel_id = 1291685593620938783  # Replace with the ID of the channel you want to send responses to
        response_channel = client.get_channel(response_channel_id)

        # Split the message content to extract action and symbol
        parts = message_content.split()
        if len(parts) == 2:
            action, symbol = parts
            symbol = symbol.upper()  # Ensure symbol is in uppercase

            if action == 'LONG':
                close_short_position(symbol)
                place_order(symbol, 'BUY', leverage)
                await response_channel.send(f"Placed a LONG order for {symbol}.")
            elif action == 'SHORT':
                close_long_position(symbol)
                place_order(symbol, 'SELL', leverage)
                await response_channel.send(f"Placed a SHORT order for {symbol}.")
            elif action == 'CLOSE1':
                close_long_position(symbol)
                await response_channel.send(f"Closed the LONG position for {symbol}.")
            elif action == 'CLOSE2':
                close_short_position(symbol)
                await response_channel.send(f"Closed the SHORT position for {symbol}.")
            elif action == 'CLOSEALL':
                close_long_position(symbol)
                close_short_position(symbol)
                await response_channel.send(f"Closed both LONG and SHORT positions for {symbol}.")
            else:
                await response_channel.send("Invalid action. Please send 'LONG' or 'SHORT' followed by the symbol.")
                #For Testing Purposes
        elif message_content == 'PRICE':
            current_price = get_current_price('BTCUSDT')
            await response_channel.send(f"Current price of BTC is {current_price}")
        elif message_content == 'TIME':
            server_time = get_server_time()
            await response_channel.send(f"Current server time: {server_time}")
        elif message_content == 'TICK':
            tick_size = get_tick_size('BTCUSDT')
            await response_channel.send(f"TICK SIZE: {tick_size}")
        elif message_content == 'QUANTITY':
            quantity = get_max_quantity('BTCUSDT')
            await response_channel.send(f"Quantity: {quantity}")
        elif message_content == 'TP1':
            position_amount = get_position_amount(api_key, secret_key, 'BTCUSDT')
            if position_amount:
                close_long_position('BTCUSDT', close_quantity=position_amount * 0.5)
                await response_channel.send("Closed 50% of the LONG position for BTCUSDT at TP1.")
        elif message_content == 'TP2':
            position_amount = get_position_amount(api_key, secret_key, 'BTCUSDT')
            if position_amount:
                close_long_position('BTCUSDT', close_quantity=position_amount)
                await response_channel.send("Closed 100% of the LONG position for BTCUSDT at TP2.")
        else:
            await response_channel.send("Invalid message content. Please send 'LONG' or 'SHORT' followed by the symbol.")
            
        
# Run the bot with the provided token
client.run(DISCORD_BOT_TOKEN)
