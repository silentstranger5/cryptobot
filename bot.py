import logging
import sys

import api
import notifier

from os import getenv

from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Message
from aiogram.types.bot_command import BotCommand
from aiogram.utils.formatting import Bold, Italic, Text, as_key_value, as_line
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

ok = load_dotenv()
if not ok:
    exit("Failed to load .env file")

# Bot token can be obtained via https://t.me/BotFather
TOKEN = getenv("BOT_TOKEN")

API_KEY = getenv("API_KEY")
API_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

REDIS_URL = getenv("REDIS_URL")

WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 8080
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "my-secret"
WEBHOOK_URL = getenv("WEBHOOK_URL")

if not(all((TOKEN, API_KEY, API_URL, REDIS_URL, WEBHOOK_URL))):
    exit("Failed to load values from the environment. Check out .env file.")

BOT_ID = int(TOKEN.split(':').pop(0))

storage = RedisStorage.from_url(REDIS_URL)
globalkey = StorageKey(
    bot_id=BOT_ID,
    chat_id=0,
    user_id=0,
)

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    text = Text(
        "Hello. This bot can track ",
        Bold("cryptocurrency prices"), "\n",
        "Check out its' commands at the ",
        Bold("menu"),
    )
    await message.answer(**text.as_kwargs())


@dp.message(Command("name"))
async def get_name_handler(message: Message):
    text = message.text.split()
    if len(text) != 2:
        text = Text(
            "Usage: /name ", 
            Italic("symbol"), "\n",
            Italic("symbol"), 
            " - Cryptocurrency Symbol (like ",
            Bold("BTC"), ")",
        )
        return await message.answer(**text.as_kwargs())

    symbol = text.pop().strip().upper()
    name = api.get_name(symbol)
    if not name:
        text = Text("Currency ", Bold(symbol), " does not exist.")
        return await message.answer(**text.as_kwargs())

    name = name.capitalize()
    text = Text("Name of ", as_key_value(symbol, name))
    return await message.answer(**text.as_kwargs())


@dp.message(Command("symbol"))
async def get_symbol_handler(message: Message):
    text = message.text.split()
    if len(text) != 2:
        text = Text(
            "Usage: /symbol ", 
            Italic("name"), "\n",
            Italic("name"), 
            " - Cryptocurrency Name (like ",
            Bold("Bitcoin"), ")",
        )
        return await message.answer(**text.as_kwargs())

    name = text.pop().strip().lower()
    symbol = api.get_symbol(name)
    if not symbol:
        text = Text("Currency ", Bold(name), " does not exist.")
        return await message.answer(**text.as_kwargs())

    name = name.capitalize()
    text = Text("Symbol of ", as_key_value(name, symbol))
    return await message.answer(**text.as_kwargs())


@dp.message(Command("price"))
async def get_price_handler(message: Message):
    text = message.text.split()
    if len(text) != 2:
        text = Text(
            "Usage: /price ", 
            Italic("symbol"), "\n",
            Italic("symbol"), 
            " - Cryptocurrency Symbol (like ",
            Bold("BTC"), ")",
        )
        return await message.answer(**text.as_kwargs())

    symbol = text[1].strip().upper()
    price = api.get_price(symbol)

    if not price:
        text = Text("Currency ", Bold(symbol), " does not exist.")
        return await message.answer(**text.as_kwargs())

    text = Text("Price of ", as_key_value(symbol, f"${price}"))
    return await message.answer(**text.as_kwargs())


@dp.message(Command("notify"))
async def notify_handler(message: Message):
    text = message.text.split()
    if len(text) not in (3, 4):
        text = Text(
            "Usage: /notify ", 
            Italic("symbol value/range"), "\n",
            Italic("symbol"),
            " - Cryptocurrency symbol (like ",
            Bold("BTC"), ")", "\n",
            Italic("value"),
            " - Price Value (positive number, like ",
            Bold("12345.67"), ")", "\n",
            Italic("range"),
            " - Price Range (ascending space-separated range,\n",
            "like ", Bold("12345.67 76543.21"), ")"
        )
        return await message.answer(**text.as_kwargs())

    symbol = text[1].strip().upper()

    if not api.get_price(symbol):
        text = Text("Currency ", Bold(symbol), " does not exist.")
        return await message.answer(**text.as_kwargs())

    price_range = text[2:4]
    if err := await validate_range(message, price_range):
        return err 

    minimal, maximal = tuple(float(value) for value in price_range)
    chat_id = message.chat.id
    await send_data(chat_id, symbol, minimal, maximal)

    text = Text(
        "Notifications had been ",
        Bold("enabled"),
        " successfully",
    )
    return await message.answer(**text.as_kwargs())


async def validate_range(message: Message, price_range: list):
    if len(price_range) == 1:
        minimal = maximal = price_range.pop()
    else:
        minimal, maximal = price_range

    for value in (minimal, maximal):
        try:
            value = float(value)
            if value < 0:
                raise ValueError
        except ValueError:
            text = Text(
                "Value ",
                Bold(value),
                " is not a positive number."
            )
            return await message.answer(**text.as_kwargs())

    minimal, maximal = float(minimal), float(maximal)
    if minimal > maximal:
        text = Text(
            "Range ",
            Bold(f"({minimal}, {maximal})"),
            " is not an ascending range."
        )
        return await message.answer(**text.as_kwargs())

    return None


async def send_data(chat_id: int, symbol: str, minimal, maximal: float):
    data = await storage.get_data(globalkey)
    if str(chat_id) not in data:
        data[str(chat_id)] = True
        await storage.update_data(globalkey, data=data)

    storagekey = StorageKey(
        bot_id=BOT_ID,
        chat_id=chat_id,
        user_id=chat_id
    )
    data = await storage.get_data(storagekey)
    data[symbol] = (minimal, maximal)
    await storage.update_data(storagekey, data=data)


@dp.message(Command("mute"))
async def mute_handler(message: Message):
    text = message.text.split()
    if len(text) != 2:
        text = Text(
            "Usage: /mute ", 
            Italic("symbol/ALL"), "\n",
            Italic("symbol"),
            " - Cryptocurrency Symbol (like ",
            Bold("BTC"), ")\n",
            Italic("ALL"),
            " - Disable all notifications"
        )
        return await message.answer(**text.as_kwargs())

    symbol = text[1].strip().upper()
    name = api.get_name(symbol)
    if not name:
        text = Text("Currency ", Bold(symbol), " does not exist.")
        return await message.answer(**text.as_kwargs())

    chat_id = message.chat.id
    await update_data(chat_id, symbol)

    text = Text(
        "Notifications had been ",
        Bold("disabled"),
        " successfully",
    )
    return await message.answer(**text.as_kwargs())


async def update_data(chat_id, symbol):
    storagekey = StorageKey(
        bot_id=BOT_ID,
        chat_id=chat_id,
        user_id=chat_id,
    )
    data = await storage.get_data(storagekey)

    if symbol == "ALL":
        await storage.set_data(storagekey, data=dict())
    elif symbol in data:
        data.pop(symbol)
        await storage.set_data(storagekey, data=data)


async def on_startup(bot: Bot):
    logging.info("Starting up...")
    commands = (
        ("name", "Query a currency name by symbol"),
        ("symbol", "Query a currency symbol by name"),
        ("price", "Query a currency price by symbol"),
        ("notify", "Set up a notification for tracking a currency price"),
        ("mute", "Disable notifications"),
    )
    commands = list(
        BotCommand(
            command=command[0],
            description=command[1],
        ) for command in commands
    )
    await bot.set_my_commands(commands)
    await bot.set_webhook(
        f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET
    )


async def on_shutdown(bot: Bot):
    logging.info("Shutting down...")
    await bot.delete_my_commands()
    await storage.close()


def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Create aiohttp.web.Application instance
    app = web.Application()

    # Create an instance of request handler,
    # aiogram has few implementations for different cases of usage
    # In this example we use SimpleRequestHandler which is designed to handle simple cases
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    )

    # Register webhook handler on application
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dp, bot=bot)

    app.update(bot=bot)
    app.cleanup_ctx.append(notifier.check_wrapper)

    # And finally start webserver
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
