# Crypto Notifier Bot

This is a Telegram Bot, which can query cryptocurrency information (name, symbol, price),
and track cryptocurrency prices with notifications.

## Commands

| Command   | Description                       |
|-----------|-----------------------------------|
| /name     | Query a currency name by symbol   |
| /symbol   | Query a currency symbol by name   |
| /price    | Query a currency price by symbol  |
| /notify   | Set up a price tracking notifications |
| /mute     | Disable notifications             |

## Description

Application roughly consists of three parts

| Module    | Description                       |
|-----------|-----------------------------------|
| bot.py    | Telegram Bot - Interacts with the user    |
| api.py    | CoinMarketCap WEB API requests    |
| notifier.py   | Notifier - Checks prices and sends notifications  |

Telegram bot contains a collection of command handlers and simple `aiohttp` server with a `webhook`
which is triggered each time user sends a message to the bot.
It is an entry point of application with primary configuration.
You can also find here a Redis storage associated with the bot. 
It is required for notifier to work.

Notifier is an additional and independent process which checks contents of the bot storage
in order to query notification data.
It is an asynchronous proccess pushed into cleanup context of the server mentioned above.
This allows notifier to work along with the server and the bot.
API file implements querying and parsing data from CoinMarketCap.

## How to build

That should provide no challenge.

```
git clone https://github.com/silentstranger5/cryptobot.git
cd cryptobot
# activate your virtual environment here
pip install -r requirements.txt
mv .env.blank .env
# fill .env file here
python bot.py
```
