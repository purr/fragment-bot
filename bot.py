import os
import re
import sys
import asyncio
import tracemalloc

from dotenv import load_dotenv
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

from config import (
    USERNAME_PATTERN,
    EMPTY_QUERY_CACHE_TIME,
    INVALID_QUERY_CACHE_TIME,
    NUMERIC_QUERY_CACHE_TIME,
)
from services.rates import start_rate_update_loop

# Import the GetGems floor price update loop
from services.getgems import start_floor_price_update_loop
from services.handler import handle_query
from services.price_converter import is_numeric_query, create_price_conversion_result

# Import our Fragment username checking service
from services.result_articles import (
    empty_query_article,
    get_ton_rate_article,
    invalid_username_article,
    get_number_floor_price_article,
)

tracemalloc.start()

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# Load environment variables
load_dotenv()

# Get bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Bot token not found in .env file")
    raise ValueError("Bot token not found in .env file")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Define pattern for validation
VALID_PATTERN = re.compile(USERNAME_PATTERN)


def is_valid_query(query: str) -> bool:
    result = bool(VALID_PATTERN.match(query))
    logger.debug("Validating query '{}': {}", query, "VALID" if result else "INVALID")
    return result


@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Handle /start command"""
    logger.info("Start command received from user {}", message.from_user.id)
    bot_info = await bot.get_me()
    username = bot_info.username

    # Create a keyboard with a button to insert an example query
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="➡️ Try it out",
                    switch_inline_query_current_chat="",
                )
            ]
        ]
    )

    await message.answer(
        f"Hi I'm @{username}\n"
        "You can use me inline for various things:\n"
        "- Check usernames on Fragment\n"
        "- Get the floor price of numbers\n"
        "- Get the current TON price\n"
        "- Convert between TON and USD\n\n"
        "Examples:\n"
        f"`@{username} username` Check username availability\n"
        f"`@{username} 100` Convert to TON/USD, vice versa\n"
        f"`@{username}` Number Floor price & TON price",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


@dp.inline_query()
async def handle_inline_query(inline_query: types.InlineQuery):
    """Handle inline queries"""
    user_id = inline_query.from_user.id
    query = inline_query.query

    if not query.strip():
        ton_rate_article = await get_ton_rate_article()
        number_floor_article = await get_number_floor_price_article()
        return await inline_query.answer(
            results=[empty_query_article, ton_rate_article, number_floor_article],
            cache_time=EMPTY_QUERY_CACHE_TIME,
        )

    processed_query = query.replace(" ", "")
    if is_numeric_query(processed_query):
        logger.debug("Numeric query detected: {}", processed_query)
        results = await create_price_conversion_result(processed_query, str(user_id))
        return await inline_query.answer(
            results=results, cache_time=NUMERIC_QUERY_CACHE_TIME
        )

    processed_query = processed_query.lower().replace("@", "")

    if is_valid_query(processed_query):
        logger.debug("Query is valid, checking on Fragment: {}", processed_query)
        return await handle_query(inline_query, processed_query, user_id)
    else:
        return await inline_query.answer(
            results=[invalid_username_article()], cache_time=INVALID_QUERY_CACHE_TIME
        )


async def main():
    # Start both update loops
    asyncio.create_task(start_rate_update_loop())
    asyncio.create_task(start_floor_price_update_loop())

    bot_info = await bot.get_me()
    logger.info(f"Bot started with username: @{bot_info.username}")
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
