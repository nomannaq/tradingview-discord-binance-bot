import discord as allert
from discord import Intents
from urllib.parse import urlencode 
from configs.binance_config import *
from order.place_order import place_order
from order.conditional_close_long import *
from order.conditional_close_short import * 
import os


api_key = os.environ['API_KEY']
secret_key = os.environ['SECRET_KEY']
account_endpoint = 'https://fapi.binance.com/fapi/v2/account'
order_endpoint = 'https://fapi.binance.com/fapi/v1/order'
exchange_info_endpoint = 'https://fapi.binance.com/fapi/v1/exchangeInfo'
intents = allert.Intents.all()
client = allert.Client(intents=intents)
leverage=10
percentage=0.8



@client.event
async def on_ready():
    print('Logged in as {0.user}'.format(client))
@client.event
async def on_message(message):
    if message.channel.id == YOUR_CHANNEL_ID:
        # Use the message content as is for case-sensitive comparison
        message_content = message.content.strip().upper()
        print(f"Received message:"+ message_content)
        
        response_channel_id = 1291685593620938783  # Replace with the ID of the channel you want to send responses to
        response_channel = client.get_channel(response_channel_id)

        # Split the message content to extract action and symbol
        #parts = message_content.split()
        #if len(parts) == 3:
            #action, symbol = parts
            #symbol = symbol.upper()  # Ensure symbol is in uppercase
        symbol='BTCUSDT'
        symbol1='XRPUSDT'
        if "LONGBTCUSDT" in message_content:
            close_short_position(symbol)
            place_order(symbol, 'BUY', leverage)
            await response_channel.send(f"Placed a LONG order for .")
        elif "SHORTBTCUSDT" in message_content:
            close_long_position(symbol)
            place_order(symbol, 'SELL', leverage)
            await response_channel.send(f"Placed a SHORT order for {symbol}.")
        elif "CLOSE1" in message_content:
            close_long_position(symbol)
            await response_channel.send(f"Closed the LONG position for {symbol}.")
        elif "CLOSE2" in message_content:
            close_short_position(symbol)
            await response_channel.send(f"Closed the SHORT position for {symbol}.")
        if "LONGXRP" in message_content:
            close_short_position(symbol1)
            place_order(symbol1, 'BUY', leverage)
            await response_channel.send(f"Placed a LONG order for .")
        elif "SHORTXRP" in message_content:
            close_long_position(symbol1)
            place_order(symbol1, 'SELL', leverage)
            await response_channel.send(f"Placed a SHORT order for {symbol}.")
        elif "CLOSEXRP1" in message_content:
            close_long_position(symbol1)
            await response_channel.send(f"Closed the LONG position for {symbol}.")
        elif "CLOSEXRP2" in message_content:
            close_short_position(symbol1)
            await response_channel.send(f"Closed the SHORT position for {symbol}.")
        elif "PRICE" in message_content:
            current_price = get_current_price(symbol)
            await response_channel.send(f"The current price for {symbol} is: {current_price}")
        elif  "CLOSEALL" in message_content:
            close_long_position(symbol)
            close_short_position(symbol)
            await response_channel.send(f"Closed both LONG and SHORT positions for {symbol}.")
            
        else:
            print("Invalid Message Content")
            
        
YOUR_CHANNEL_ID = 123456
Server_Response_Channel_ID= 123456
# Replace 'YOUR_BOT_TOKEN' with your Discord bot token
client.run('your discord bot token')