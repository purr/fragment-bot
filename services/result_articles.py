from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputTextMessageContent,
    InlineQueryResultArticle,
)

from config import TON_THUMBNAIL_URL, TON_DECIMAL_PLACES, FRAGMENT_THUMBNAIL_URL
from services.rates import get_ton_price
from services.getgems import get_number_floor_price_message
from services.price_converter import format_number, create_price_keyboard


def create_price_button(username: str, price_info: dict) -> InlineKeyboardButton:
    """
    Create a button with price information for a username

    Args:
        username: The username being checked
        price_info: Dictionary containing price information

    Returns:
        InlineKeyboardButton: Button with price information
    """
    ton_price = price_info.get("ton", "?")
    usd_price = price_info.get("usd", "?")

    button_text = f"💎 {ton_price} TON (≈ ${usd_price})"
    url = f"https://fragment.com/username/{username}"

    return InlineKeyboardButton(text=button_text, url=url)


def create_sale_price_button(username: str, price: str) -> InlineKeyboardButton:
    """
    Create a button with sale price information for a sold username

    Args:
        username: The username that was sold
        price: The price the username was sold for (in TON)

    Returns:
        InlineKeyboardButton: Button with sale price information
    """
    button_text = f"💰 {price} TON"
    url = f"https://fragment.com/username/{username}"

    return InlineKeyboardButton(text=button_text, url=url)


def create_wallet_button(name: str, link: str, has_bids: bool) -> InlineKeyboardButton:
    emoji = "👤" if not has_bids else "🥇"
    button_text = f"{emoji} {name}"

    return InlineKeyboardButton(text=button_text, url=link)


def create_telegram_button(name: str) -> InlineKeyboardButton:

    if "t.me" in name:
        username = name.replace(".t.me", "")
        return InlineKeyboardButton(
            text=f"📲 @{username}", url="https://t.me/" + username
        )
    else:
        return None


def create_countdown_button(username: str, ends_in: str) -> InlineKeyboardButton:
    """
    Create a button showing the countdown information (Ends in)

    Args:
        username: The username being checked
        ends_in: Formatted countdown string

    Returns:
        InlineKeyboardButton: Button with countdown information
    """
    button_text = f"⏱️ {ends_in}"
    url = f"https://fragment.com/username/{username}"

    return InlineKeyboardButton(text=button_text, url=url)


def create_buy_now_button(username: str, buy_now_info: dict) -> InlineKeyboardButton:
    """
    Create a button for the Buy It Now option in auctions

    Args:
        username: The username being checked
        buy_now_info: Dictionary containing Buy Now information

    Returns:
        InlineKeyboardButton: Button with Buy Now information
    """
    ton_amount = buy_now_info.get("ton", "?")
    button_text = f"💰 BIN: {ton_amount} TON"
    url = f"https://fragment.com/username/{username}"

    return InlineKeyboardButton(text=button_text, url=url)


async def create_enhanced_auction_source_button(
    tonapi_data: dict,
):
    """
    Create an enhanced button showing the auction source with additional beneficiary info.
    For Fragment mints, returns a standard button. For other beneficiaries, fetches additional info.

    Args:
        tonapi_data: Dictionary containing TONAPI auction data

    Returns:
        InlineKeyboardButton: Button with auction source information, or None if data is invalid
    """
    # Check if we have valid data
    if not tonapi_data or "auction_config" not in tonapi_data:
        return None

    auction_config = tonapi_data["auction_config"]

    # Check for success and decoded data
    if not auction_config.get("success") or "decoded" not in auction_config:
        return None

    # Get the beneficiary address from the decoded data
    beneficiary = auction_config["decoded"].get("beneficiar")
    if not beneficiary:
        return None

    # Check if it's a Fragment mint based on the beneficiary address
    fragment_mint_address = (
        "0:408da3b28b6c065a593e10391269baaa9c5f8caebc0c69d9f0aabbab2a99256b"
    )

    if beneficiary == fragment_mint_address:
        button_text = "🏛️ Fragment Mint"
        url = "https://fragment.com"

    else:
        button_text = f"👤 User Auction"
        url = f"https://tonviewer.com/{beneficiary}"

    return InlineKeyboardButton(text=button_text, url=url)


def invalid_username_article():
    return InlineQueryResultArticle(
        id="invalid",
        title="Invalid Username Format",
        description="Query must >4 characters and start with a letter",
        input_message_content=InputTextMessageContent(
            message_text="Usernames must start with a letter, be at least 4 characters long, and can contain letters, numbers, and underscores."
        ),
        thumbnail_url=FRAGMENT_THUMBNAIL_URL,
    )


def error_checking_username_article(processed_query: str):
    # Escape Markdown special characters in the username
    escaped_query = escape_markdown(processed_query)

    return InlineQueryResultArticle(
        id="error",
        title="Error checking username",
        description=f"Could not check '{processed_query}' on Fragment",
        input_message_content=InputTextMessageContent(
            message_text=f"Error checking username `{escaped_query}` on Fragment. Please try again later.",
            parse_mode=ParseMode.MARKDOWN,
        ),
        thumbnail_url=FRAGMENT_THUMBNAIL_URL,
    )


# async def process_fragment_page(username: str, html_content: str) -> dict:
#
#     if status_text == "On auction":
#
#         # Fetch TONAPI auction config for auctions without ownership history
#         tonapi_data = await fetch_auction_config_from_tonapi(username, html_content)
#         if tonapi_data:
#             result["tonapi_data"] = tonapi_data
#             logger.debug(f"Added TONAPI data for auction: {username}")


# async def username_result_article(result: dict):
#     # Check if this is a minimum bid (no bids yet)
#     has_minimum_bid = False
#     highest_bid = result.get("highest_bid", {})
#     if highest_bid and highest_bid.get("is_minimum_bid", False):
#         has_minimum_bid = True
#
#
#     # First row: price button for available/for sale items
#     if price_info and status in ["Available", "For sale"]:
#         keyboard_rows.append([create_price_button(username, price_info)])
#
#     # For auction items, create separate rows for bid and bidder
#     if status == "On auction":
#         # Add highest bid button in its own row if available
#         if highest_bid:
#             keyboard_rows.append([create_price_button(username, highest_bid)])
#
#         # Add Buy Now button if available
#         buy_now_info = result.get("buy_now_info")
#         if buy_now_info:
#             keyboard_rows.append([create_buy_now_button(username, buy_now_info)])
#
#         # Add highest bidder button in its own row if available
#         bidder_info = result.get("highest_bidder")
#         if bidder_info:
#             telegram_button = create_telegram_button(bidder_info)
#             if telegram_button:
#                 keyboard_rows.append(
#                     [
#                         create_wallet_button(bidder_info, has_minimum_bid),
#                         telegram_button,
#                     ]
#                 )
#             else:
#                 keyboard_rows.append(
#                     [create_wallet_button(bidder_info, has_minimum_bid)]
#                 )
#         # Add enhanced auction source button if TONAPI data is available


def escape_markdown(text: str) -> str:
    """
    Escape Markdown special characters to prevent formatting issues

    Args:
        text: The text to escape

    Returns:
        The escaped text
    """
    # Characters that need to be escaped in Markdown
    special_chars = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]

    for char in special_chars:
        text = text.replace(char, f"\\{char}")

    return text


# Restore the original empty query article
empty_query_article = InlineQueryResultArticle(
    id="empty_query",
    title="Enter a username",
    description="Type a username to retrieve Fragment information",
    input_message_content=InputTextMessageContent(
        message_text="Please enter a valid Telegram username to retrieve Fragment information.",
    ),
    thumbnail_url=FRAGMENT_THUMBNAIL_URL,
)


async def get_number_floor_price_article():
    """
    Create the number floor price article
    """
    # Get the number floor price message
    floor_price_info = await get_number_floor_price_message()

    # Create the keyboard with buttons
    keyboard = None
    buttons = floor_price_info.get("buttons", [])

    if buttons:
        # Convert to InlineKeyboardButton objects
        keyboard_buttons = []
        for button_info in buttons:
            if isinstance(button_info, list):
                # Handle a row of multiple buttons
                row = []
                for btn in button_info:
                    row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
                keyboard_buttons.append(row)
            else:
                # Handle a single button in a row
                keyboard_buttons.append(
                    [
                        InlineKeyboardButton(
                            text=button_info["text"], url=button_info["url"]
                        )
                    ]
                )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    return InlineQueryResultArticle(
        id="number_floor_price",
        title=floor_price_info["title"],
        description=floor_price_info["description"],
        input_message_content=InputTextMessageContent(
            message_text=floor_price_info["message"],
            parse_mode=ParseMode.MARKDOWN,
        ),
        reply_markup=keyboard,
        thumbnail_url="https://storage.getblock.io/web/web/images/marketplace/Fragment/photo_2024-07-23_22-06-50.jpg",
    )


async def get_ton_rate_article():

    ton_price, source_info = await get_ton_price()

    if ton_price is None:
        text = "⚠️ *Price Data Unavailable*\n\nUnable to fetch current TON price. Please try again later."
        title = "⚠️ TON Rate Unavailable"
        description = "Unable to fetch current TON price"
        keyboard = None
    else:
        text = f"💎 *Current TON Rate*"
        title = f"TON Rate: ${format_number(ton_price, TON_DECIMAL_PLACES)}"
        description = "Enter a number to convert between USD and TON"
        keyboard = create_price_keyboard(ton_price, source_info)

    return InlineQueryResultArticle(
        id="ton_rate",
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=text, parse_mode="Markdown"
        ),
        reply_markup=keyboard,
        thumbnail_url=TON_THUMBNAIL_URL,
    )
