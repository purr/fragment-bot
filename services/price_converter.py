import re

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputTextMessageContent,
    InlineQueryResultArticle,
)

from config import TON_THUMBNAIL_URL, TON_DECIMAL_PLACES, DEFAULT_DECIMAL_PLACES
from services.rates import get_ton_price, convert_ton_to_usd, convert_usd_to_ton

# Regular expression to identify numeric inputs with optional commas
NUMERIC_PATTERN = re.compile(r"^[\d,\.]+$")


def is_numeric_query(query: str) -> bool:
    """Check if a query is numeric (can be price)"""
    return bool(NUMERIC_PATTERN.match(query))


def format_number(number: float, decimal_places: int = DEFAULT_DECIMAL_PLACES) -> str:
    """Format a number with commas as thousands separators and remove unnecessary trailing zeros"""
    # Format with the specified decimal places
    formatted = f"{number:,.{decimal_places}f}"

    # Remove trailing zeros and decimal point if appropriate
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")

    return formatted


def process_number_input(query: str) -> float:
    """Process numeric input, replacing commas with periods"""
    # Replace commas with periods for float conversion
    processed = query.replace(",", ".")
    try:
        return float(processed)
    except ValueError:
        return 0.0


async def create_price_conversion_result(query: str, query_id: str):
    """Create price conversion result for an inline query"""
    processed_number = process_number_input(query)

    # Get current TON price
    ton_price, price_info = await get_ton_price()

    if ton_price is None:
        return [create_price_error_article(query_id)]

    # Calculate average price from both sources if available
    source1_price = price_info.get("source1")
    source2_price = price_info.get("source2")

    if source1_price and source2_price:
        # Use the average of both sources
        average_price = (source1_price + source2_price) / 2
        # Update the ton_price to use the average
        ton_price = average_price

    # For any number, show both conversions
    return [
        create_dual_conversion_article(
            processed_number, ton_price, price_info, query_id
        )
    ]


def create_price_error_article(query_id: str):
    """Create an error article for when price data is unavailable"""
    return InlineQueryResultArticle(
        id=f"price_error_{query_id}",
        title="⚠️ Price Data Unavailable",
        description="Unable to fetch current TON price. Please try again later.",
        input_message_content=InputTextMessageContent(
            message_text="⚠️ *Price Data Unavailable*\n\nUnable to fetch current TON price. Please try again later.",
            parse_mode="Markdown",
        ),
        thumbnail_url=TON_THUMBNAIL_URL,
    )


def create_dual_conversion_article(
    amount: float,
    ton_price: float,
    price_info: dict,
    query_id: str,
):
    """Create an article showing both USD to TON and TON to USD conversions"""
    # Calculate conversions
    ton_amount = convert_usd_to_ton(amount)
    usd_amount = convert_ton_to_usd(amount)

    if ton_amount is None or usd_amount is None:
        return create_price_error_article(query_id)

    title = f"💱 USD ⇆ TON: {format_number(amount)}"
    description = f"💎 1 TON = ${format_number(ton_price, TON_DECIMAL_PLACES)}"

    keyboard = create_price_keyboard(ton_price, price_info)

    message_text = (
        f"💵 ${format_number(amount)} = *{format_number(ton_amount, TON_DECIMAL_PLACES)} TON*\n"
        f"💎 {format_number(amount)} TON = *${format_number(usd_amount)}* \n\n"
    )

    return InlineQueryResultArticle(
        id=f"price_conversion_{query_id}",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=message_text, parse_mode="Markdown"
        ),
        reply_markup=keyboard,
        thumbnail_url=TON_THUMBNAIL_URL,
    )


def create_price_keyboard(ton_price: float, price_info: dict) -> InlineKeyboardMarkup:
    """Create a keyboard with price source information"""
    source1_price = price_info.get("source1")
    source2_price = price_info.get("source2")

    source1_text = (
        f"CoinGecko: ${format_number(source1_price, TON_DECIMAL_PLACES)}"
        if source1_price
        else "CoinGecko: N/A"
    )
    source2_text = (
        f"Binance: ${format_number(source2_price, TON_DECIMAL_PLACES)}"
        if source2_price
        else "Binance: N/A"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💎 1 TON = ${format_number(ton_price, TON_DECIMAL_PLACES)}",
                    callback_data="rate_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text=source1_text, url="https://www.coingecko.com/en/coins/toncoin"
                ),
                InlineKeyboardButton(
                    text=source2_text,
                    url="https://www.binance.com/en/price/the-open-network",
                ),
            ],
        ]
    )

    return keyboard
