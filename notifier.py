import asyncio

import api
import bot

from aiohttp import web
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.utils.formatting import Text, Bold, Italic
from contextlib import suppress


async def check_wrapper(app: web.Application):
    bot = app.get("bot")
    task = asyncio.create_task(check_prices(bot))

    yield

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


async def check_prices(tbot: Bot):
    data = await bot.storage.get_data(bot.globalkey)
    chat_ids = data.keys()
    while True:
        for chat_id in chat_ids:
            chat_id = int(chat_id)
            storagekey = StorageKey(
                bot_id=bot.BOT_ID,
                chat_id=chat_id,
                user_id=chat_id,
            )
            chat_data = await bot.storage.get_data(storagekey)
            notifications = list()
            for symbol in chat_data:
                minimal, maximal = chat_data.get(symbol)
                price = api.get_price(symbol)
                if minimal <= price <= maximal:
                    notifications.append((symbol, minimal, maximal))
            if len(notifications) > 0:
                await tbot.send_message(
                    chat_id=chat_id,
                    text="Cryptocurrency Price is now within the specified range."
                )
            for record in notifications:
                symbol, minimal, maximal = record
                text = Text("Currency ",
                    Bold(symbol),
                    " is now within a range of ",
                    Italic(f"${minimal} - ${maximal}")
                )
                await tbot.send_message(
                    chat_id,
                    **text.as_kwargs(),
                )
        await asyncio.sleep(60)
