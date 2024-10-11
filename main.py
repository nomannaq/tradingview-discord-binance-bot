import os
import discord
import requests
import hashlib
import hmac
import time
from urllib.parse import urlencode
from discord.ext import commands

# Load environment variables 
DISCORD_BOT_TOKEN = 'Add your Discord bot token here'  # Token for the Discord bot to interact with the Discord API
BINANCE_API_KEY = 'Your Binance API Key goes here'  # API key to authenticate with Binance
BINANCE_SECRET_KEY = 'Your Binance Secret Key goes here'  # Secret key for signing requests to Binance
YOUR_CHANNEL_ID = 123456789  # Replace with your actual channel ID where the bot will listen for messages

# Discord bot setup with default intents to allow the bot to read messages
intents = discord.Intents.default()
intents.messages = True
client = commands.Bot(command_prefix="!", intents=intents)  # Bot uses "!" as the command prefix

# Base URL and headers for Binance API requests
BASE_URL = "https://fapi.binance.com"
HEADERS = {"X-MBX-APIKEY": BINANCE_API_KEY}

# Fetch the current price of a symbol (e.g., BTCUSDT) from Binance
def get_current_price(symbol):
    try:
        endpoint = f"{BASE_URL}/fapi/v1/ticker/price"
        response = requests.get(endpoint, params={"symbol": symbol})
        if response.status_code == 200:
            # Parse the response and return the current price
            price = float(response.json()['price'])
            print(f"Current price for {symbol}: {price}")
            return price
        else:
            # Handle API errors
            print(f"Error fetching price. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        # Handle any exceptions that occur during the API call
        print(f"Exception in getting current price: {e}")
        return None

# Fetch the tick size for a given symbol, which is used for proper rounding of price
def get_tick_size(symbol):
    try:
        endpoint = f"{BASE_URL}/fapi/v1/exchangeInfo"
        response = requests.get(endpoint)
        if response.status_code == 200:
            # Loop through all symbols to find the tick size for the requested symbol
            symbols_info = response.json()['symbols']
            for sym in symbols_info:
                if sym['symbol'] == symbol:
                    for filter in sym['filters']:
                        if filter['filterType'] == 'PRICE_FILTER':
                            tick_size = float(filter['tickSize'])
                            print(f"Tick size for {symbol}: {tick_size}")
                            return tick_size
        else:
            # Handle API errors
            print(f"Error fetching exchange info. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        # Handle any exceptions that occur during the API call
        print(f"Exception in getting tick size: {e}")
        return None

# Fetch available balance (in USDT) from Binance futures account
def get_available_balance():
    try:
        endpoint = f"{BASE_URL}/fapi/v2/balance"
        timestamp = int(time.time() * 1000)  # Generate a timestamp for request signing
        payload = {'timestamp': timestamp}  # Payload containing the timestamp
        query_string = urlencode(payload)
        
        # Sign the request using HMAC with SHA256 and the Binance secret key
        signature = hmac.new(BINANCE_SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        payload['signature'] = signature
        
        # Make the request to get account balances
        response = requests.get(endpoint, params=payload, headers=HEADERS)
        if response.status_code == 200:
            balances = response.json()
            # Look for USDT balance and return available balance
            for asset in balances:
                if asset['asset'] == 'USDT':
                    available_balance = float(asset['availableBalance'])
                    print(f"Available balance in USDT: {available_balance}")
                    return available_balance
            return 0.0  # Return zero if no balance is found
        else:
            # Handle API errors
            print(f"Error fetching balance. Status code: {response.status_code}, Message: {response.text}")
            return None
    except Exception as e:
        # Handle any exceptions that occur during the API call
        print(f"Exception in getting available balance: {e}")
        return None

# Calculate maximum quantity of the symbol that can be bought based on available balance and current price
def get_max_quantity(symbol):
    available_balance = get_available_balance()  # Get available USDT balance
    if available_balance is not None:
        current_price = get_current_price(symbol)  # Get current market price of the symbol
        if current_price:
            # Calculate the maximum quantity by using 99% of the balance (to avoid rounding issues)
            max_quantity = available_balance / current_price * 0.99
            # Fetch the tick size for proper rounding
            tick_size = get_tick_size(symbol)
            if tick_size:
                # Round the calculated quantity to the nearest tick size
                max_quantity = round(max_quantity - (max_quantity % tick_size), 2)
                print(f"Calculated max quantity for {symbol}: {max_quantity}")
                return max_quantity
    print("Could not calculate max quantity due to insufficient data.")
    return None

# Place a limit order on Binance futures market (buy/sell)
def place_limit_order(symbol, side, leverage, price, quantity):
    try:
        timestamp = int(time.time() * 1000)  # Generate a timestamp for request signing
        payload = {
            'symbol': f'{symbol.upper()}USDT',  # Trade pair, e.g., BTCUSDT
            'side': side,  # 'BUY' for long or 'SELL' for short
            'type': 'LIMIT',  # Limit order type
            'price': round(price, 2),  # Order price (rounded to 2 decimal places)
            'quantity': quantity,  # Quantity to trade
            'timeInForce': 'GTC',  # Good 'Til Cancelled order
            'timestamp': timestamp
        }
        
        # Sign the request using HMAC with SHA256 and the Binance secret key
        query_string = urlencode(payload)
        signature = hmac.new(BINANCE_SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        payload['signature'] = signature
        
        # Make the POST request to place the order
        order_endpoint = f"{BASE_URL}/fapi/v1/order"
        response = requests.post(order_endpoint, params=payload, headers=HEADERS)
        
        if response.status_code == 200:
            # Order successfully placed, print details
            print(f"{side} limit order successfully placed. Details:")
            print(response.json())
        else:
            # Handle errors during order placement
            print(f"Error placing order. Status code: {response.status_code}, Message: {response.text}")
    except Exception as e:
        # Handle any exceptions that occur during the order placement
        print(f"Exception in placing limit order: {e}")

# Event triggered when the bot is ready and logged in
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')  # Prints bot information when connected

# Event to handle incoming messages in Discord
@client.event
async def on_message(message):
    if message.channel.id == YOUR_CHANNEL_ID:  # Only listen to a specific channel
        message_content = message.content.strip().upper()  # Process message text and convert to uppercase
        
        # Handle 'LONG' command to place a long (buy) order
        if 'LONG' in message_content:
            current_price = get_current_price('BTCUSDT')
            quantity = get_max_quantity('BTCUSDT')
            if current_price and quantity:
                limit_price = current_price * 0.99  # Buy slightly below the current price
                place_limit_order('BTC', 'BUY', 10, limit_price, quantity)
            else:
                await message.channel.send("Could not fetch current price or calculate quantity for LONG.")
        
        # Handle 'SHORT' command to place a short (sell) order
        elif 'SHORT' in message_content:    
            current_price = get_current_price('BTCUSDT')
            quantity = get_max_quantity('BTCUSDT')
            if current_price and quantity:
                limit_price = current_price * 1.01  # Sell slightly above the current price
                place_limit_order('BTC', 'SELL', 10, limit_price, quantity)
            else:
                await message.channel.send("Could not fetch current price or calculate quantity for SHORT.")

        # Additional commands for closing positions, checking prices, etc.
        elif 'CLOSE1' in message_content:
            close_long_position('BTC')
        elif 'CLOSE2' in message_content:
            close_short_position('BTC')
        elif 'PRICE' in message_content:
            current_price = get_current_price('BTCUSDT')
            await message.channel.send(f"Current price of BTC is {current_price}")
        elif 'TIME' in message_content:
            server_time = int(time.time())
            await message.channel.send(f"Current server time: {server_time}")
        elif 'QUANTITY' in message_content:
            quantity = get_max_quantity('BTCUSDT')
            await message.channel.send(f"Maximum quantity: {quantity}")
        else:
            await message.channel.send("Invalid command. Use 'LONG', 'SHORT', 'CLOSE1', 'CLOSE2', 'PRICE', or 'TIME'.")

# Run the bot with the provided token
client.run(DISCORD_BOT_TOKEN)
