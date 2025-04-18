import re
import asyncio

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardMarkup,
    InputTextMessageContent,
    InlineQueryResultArticle,
)

from config import (
    ERROR_CACHE_TIME,
    FRAGMENT_MINT_ADDRESS,
    FRAGMENT_THUMBNAIL_URL,
    FRAGMENT_API_REQUEST_DELAY,
    USERNAME_RESULT_CACHE_TIME,
    UNAVAILABLE_USERNAME_CACHE_TIME,
)
from services.result_articles import (
    escape_markdown,
    create_price_button,
    create_wallet_button,
    create_buy_now_button,
    create_telegram_button,
    create_sale_price_button,
    error_checking_username_article,
    create_enhanced_auction_source_button,
)


async def get_fragment_page(username: str):

    url = f"https://fragment.com/username/{username}"

    # Using aiohttp for async requests
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as response:
            # Check if we were redirected (indicating username is unavailable on Fragment)
            if response.status in (301, 302, 303, 307, 308):
                logger.debug(
                    f"Redirect detected for {username}, status code: {response.status}"
                )
                return None

            if response.status == 200:
                return await response.text()

            logger.warning(
                f"Unexpected response for {username}, status code: {response.status}"
            )
            return False


async def get_username_status(soup: BeautifulSoup) -> str:
    status_span = soup.select_one(".tm-section-header-status")
    if status_span:
        return status_span.text.strip()
    return None


def available_price_info(soup: BeautifulSoup, username: str):
    try:
        price_container = soup.select_one(".tm-section-bid .table-cell-value.tm-value")
        if not price_container:
            price_container = soup.select_one(".table-cell.table-cell-oneline")
            if not price_container:
                return None

        ton_value_element = price_container.select_one(".icon-ton") or price_container
        ton_amount = ton_value_element.text.strip() if ton_value_element else None

        usd_element = price_container.find_next_sibling(
            "div", class_="table-cell-desc"
        ) or price_container.find("div", class_="table-cell-desc")
        usd_amount = None
        if usd_element:
            usd_text = usd_element.text.strip()
            usd_match = re.search(r"\$([0-9,.]+)", usd_text)
            if usd_match:
                usd_amount = usd_match.group(1)

        if ton_amount or usd_amount:
            return create_price_button(username, {"ton": ton_amount, "usd": usd_amount})

        return None

    except Exception as e:
        logger.error(f"Error extracting price info: {str(e)}")
        return None


def most_recent_wallet_info(soup: BeautifulSoup, has_bids: bool):
    try:
        bid_table = soup.select_one(".tm-table-wrap table tbody")
        if not bid_table:
            logger.warning("Could not find bid table body")
            return None

        first_bid_row = bid_table.select_one("tr")
        if not first_bid_row:
            logger.warning("Could not find first bid row")
            return None

        wallet_cell = first_bid_row.select("td")[-1]
        wallet_link_element = wallet_cell.select_one("a.tm-wallet")

        if not wallet_link_element or not wallet_link_element.has_attr("href"):
            logger.warning(
                "Could not find wallet link element or href in first bid row"
            )
            return None

        wallet_link = wallet_link_element["href"]

        bidder_name = None
        short_name_element = wallet_link_element.select_one("span.short")
        if short_name_element:
            bidder_name = short_name_element.text.strip()
        else:
            head_element = wallet_link_element.select_one("span.head")
            tail_element = wallet_link_element.select_one("span.tail")

            head = head_element.text.strip()
            tail = tail_element.text.strip()

            bidder_name = f"{head[:5]}...{tail[-5:]}"

        buttons = []

        # Add wallet button
        wallet_button = create_wallet_button(
            bidder_name or "Unknown Bidder", wallet_link, has_bids
        )
        buttons.append(wallet_button)

        # Add telegram button if name exists and isn't a wallet address
        if bidder_name and not bidder_name.startswith(("EQ", "UQ")):
            telegram_button = create_telegram_button(bidder_name)
            if telegram_button:
                buttons.append(telegram_button)

        return buttons if buttons else None

    except Exception as e:
        logger.error(f"Error extracting highest bidder info: {str(e)}")
        return None


def extract_minimum_bid_info(soup: BeautifulSoup, username: str):

    try:
        if "Highest Bid" not in soup.text:

            tables = soup.find_all("table")
            for table in tables:
                headers = table.find_all("th")
                if any(header and "Minimum Bid" in header.text for header in headers):
                    first_cell = table.find("td")
                    if first_cell:
                        ton_value = first_cell.select_one(".table-cell-value")
                        ton_amount = ton_value.text.strip() if ton_value else None

                        usd_element = first_cell.select_one(".table-cell-desc")
                        usd_amount = None
                        if usd_element:
                            usd_text = usd_element.text.strip()
                            usd_match = re.search(r"\$([0-9,.]+)", usd_text)
                            if usd_match:
                                usd_amount = usd_match.group(1)

                        if ton_amount or usd_amount:
                            logger.debug(
                                f"Found minimum bid: {ton_amount} TON (${usd_amount})"
                            )
                            return create_price_button(
                                username, {"ton": ton_amount, "usd": usd_amount}
                            )

        return None

    except Exception as e:
        logger.error(f"Error extracting minimum bid info: {str(e)}")
        return None


def extract_highest_bid_info(soup: BeautifulSoup, username: str):

    try:
        tables = soup.find_all("table")

        for table in tables:
            header = table.find("th")
            if header and "Highest Bid" in header.text:
                first_cell = table.find("td")
                if first_cell:
                    ton_value = first_cell.find("div", class_="table-cell-value")
                    ton_amount = ton_value.text.strip() if ton_value else None

                    usd_element = first_cell.find("div", class_="table-cell-desc")
                    usd_amount = None
                    if usd_element:
                        usd_text = usd_element.text.strip()
                        usd_match = re.search(r"\$([0-9,.]+)", usd_text)
                        if usd_match:
                            usd_amount = usd_match.group(1)

                    if ton_amount or usd_amount:
                        return create_price_button(
                            username, {"ton": ton_amount, "usd": usd_amount}
                        )

                logger.warning("Found bid table but couldn't extract bid amounts")
                break

        logger.warning("Could not find auction bid table")
        return None

    except Exception as e:
        logger.error(f"Error extracting highest bid info: {str(e)}")
        return None


def extract_buy_now_info(soup: BeautifulSoup, username: str):

    try:
        buy_now_button = soup.select_one(".btn.btn-primary.js-buy-now-btn")

        if not buy_now_button:
            return None

        if buy_now_button.has_attr("data-bid-amount"):
            bid_amount_str = buy_now_button["data-bid-amount"]

            bid_amount = bid_amount_str.replace(",", "")

            amount_numeric = int(bid_amount)
            amount_formatted = f"{amount_numeric:,}"

            ton_amount_element = buy_now_button.select_one(".tm-amount")
            displayed_amount = (
                ton_amount_element.text.strip()
                if ton_amount_element
                else amount_formatted
            )

            logger.debug(f"Found Buy Now button with amount: {displayed_amount} TON")
            return create_buy_now_button(
                username, {"ton": displayed_amount, "amount_numeric": amount_numeric}
            )

        return None

    except Exception as e:
        logger.error(f"Error extracting Buy Now info: {str(e)}")
        return None


def extract_ends_in_info(soup: BeautifulSoup) -> str | None:

    try:
        countdown_section = soup.find("div", class_="tm-section-countdown")
        if not countdown_section:
            logger.warning("Could not find countdown section")
            return None

        time_element = countdown_section.find("time", class_="tm-countdown-timer")
        if not time_element:
            logger.warning("Could not find countdown timer element")
            return None

        days_digit = time_element.select_one(".digit.timer-d")
        days_text = (
            days_digit["data-val"]
            if days_digit and days_digit.has_attr("data-val")
            else "0 days"
        )

        hour0 = time_element.select_one(".digit.timer-h0")
        hour1 = time_element.select_one(".digit.timer-h1")
        hours_text = ""
        if (
            hour0
            and hour1
            and hour0.has_attr("data-val")
            and hour1.has_attr("data-val")
        ):
            hours_text = f"{hour0['data-val']}{hour1['data-val']}"
        else:
            hours_text = "00"

        min0 = time_element.select_one(".digit.timer-m0")
        min1 = time_element.select_one(".digit.timer-m1")
        mins_text = ""
        if min0 and min1 and min0.has_attr("data-val") and min1.has_attr("data-val"):
            mins_text = f"{min0['data-val']}{min1['data-val']}"
        else:
            mins_text = "00"

        if "0 days" in days_text:
            formatted_time = f"{int(hours_text)}h {int(mins_text)}m"
        else:
            formatted_time = f"{int(days_text.replace(' days', '').replace(' day', ''))}d {int(hours_text)}h {int(mins_text)}m"

        return formatted_time

    except Exception as e:
        logger.error(f"Error extracting countdown info: {str(e)}", exc_info=True)
        return None


def extract_sold_price_info(soup: BeautifulSoup, username: str):
    try:
        sale_tables = []
        for th in soup.find_all("th"):
            if "Sale Price" in th.text:
                parent_table = th.find_parent("table")
                if parent_table:
                    sale_tables.append(parent_table)
                    break

        if not sale_tables:
            logger.warning("No tables with 'Sale Price' header found")
            return None

        sale_table = sale_tables[0]

        price_value_div = sale_table.select_one("td div.table-cell-value")
        if not price_value_div:
            logger.warning("Could not find price value div in the sale table")
            return None

        price = price_value_div.text.strip()

        if price:
            return create_sale_price_button(username, price)

        return None

    except Exception as e:
        logger.error(f"Error extracting sold price info: {str(e)}", exc_info=True)
        return None


def extract_sold_owner_info(soup: BeautifulSoup):
    try:
        sale_tables = []
        for th in soup.find_all("th"):
            if "Sale Price" in th.text:
                parent_table = th.find_parent("table")
                if parent_table:
                    sale_tables.append(parent_table)
                    break

        if not sale_tables:
            logger.warning("No tables with 'Sale Price' header found")
            return None

        sale_table = sale_tables[0]

        wallet_link = sale_table.select_one("td a.tm-wallet")
        owner_info = {}

        if wallet_link and wallet_link.has_attr("href"):
            owner_info["link"] = wallet_link["href"]

            # First check if there's a short name element
            short_name_element = wallet_link.select_one("span.short")
            if short_name_element:
                owner_info["name"] = short_name_element.text.strip()
            else:
                # Fall back to head/tail spans
                head_span = wallet_link.select_one("span.head")
                tail_span = wallet_link.select_one("span.tail")

                if head_span and tail_span:
                    head_text = head_span.text.strip()
                    tail_text = tail_span.text.strip()
                    owner_info["name"] = f"{head_text[:5]}...{tail_text[-5:]}"
                else:
                    owner_info["name"] = "Unknown Owner"
        else:
            logger.warning("Could not find wallet link in the sale table")
            return None

        buttons = []

        if owner_info.get("link"):
            wallet_button = create_wallet_button(
                owner_info.get("name", "Unknown Owner"), owner_info.get("link"), False
            )
            buttons.append(wallet_button)

        if owner_info.get("name"):
            telegram_button = create_telegram_button(owner_info.get("name"))
            if telegram_button:
                buttons.append(telegram_button)

        return buttons if buttons else None

    except Exception as e:
        logger.error(f"Error extracting sold owner info: {str(e)}", exc_info=True)
        return None


def extract_for_sale_owner_info(soup: BeautifulSoup):
    """
    Extract owner information for usernames with "For sale" status
    by looking at the last bid information
    """
    try:
        # Find bid history table (similar to how we extract highest bidder info)
        bid_table = soup.select_one(".tm-table-wrap table tbody")
        if not bid_table:
            logger.warning("Could not find bid history table for 'For sale' username")
            return None

        # Find the first row (most recent bid) in the table
        first_bid_row = bid_table.find("tr")
        if not first_bid_row:
            logger.warning("Could not find any bid rows in the history table")
            return None

        # Find the wallet link in the last cell
        cells = first_bid_row.find_all("td")
        if not cells or len(cells) < 3:  # Bid tables typically have at least 3 columns
            logger.warning("Bid row doesn't have enough cells")
            return None

        wallet_cell = cells[-1]  # Last cell contains the wallet
        wallet_link = wallet_cell.find("a", class_="tm-wallet")

        if not wallet_link or not wallet_link.has_attr("href"):
            logger.warning("Could not find wallet link in bid row")
            return None

        # Extract owner info
        owner_info = {"link": wallet_link["href"]}

        # First check if there's a short name element
        short_name_element = wallet_link.select_one("span.short")
        if short_name_element:
            owner_info["name"] = short_name_element.text.strip()
        else:
            # Fall back to head/tail spans
            head_span = wallet_link.find("span", class_="head")
            tail_span = wallet_link.find("span", class_="tail")

            head_text = head_span.text.strip()
            tail_text = tail_span.text.strip()
            owner_info["name"] = f"{head_text[:5]}...{tail_text[-5:]}"

        buttons = []

        # Add wallet button
        wallet_button = create_wallet_button(
            owner_info.get("name", "Unknown Owner"), owner_info.get("link"), False
        )
        buttons.append(wallet_button)

        # Add telegram button if name exists
        if owner_info.get("name"):
            telegram_button = create_telegram_button(owner_info.get("name"))
            if telegram_button:
                buttons.append(telegram_button)

        return buttons if buttons else None

    except Exception as e:
        logger.error(f"Error extracting 'For sale' owner info: {str(e)}", exc_info=True)
        return None


def get_status_message(status: str, username: str):
    if status == "Unavailable":
        status_emoji = "❌"
    elif status == "Sold":
        status_emoji = "🔴"
    elif status == "Taken":
        status_emoji = "🟠"
    else:
        status_emoji = "🟢"

    return f"{status_emoji} @{username} is *{status.lower()}*"


async def fetch_auction_config_from_tonapi(
    username: str, html_content: str
) -> dict | None:
    """
    For auctions without ownership history, fetch auction details from TONAPI.

    This function checks if "Ownership History" is missing in the HTML,
    then makes requests to TONAPI to get advanced auction configuration.

    Args:
        username: The username being checked
        html_content: HTML content from Fragment.com

    Returns:
        dict: Contains TONAPI auction configuration info, or None if not applicable/available
    """
    try:
        # First check if "Ownership History" doesn't exist in the HTML
        if "Ownership History" not in html_content:
            logger.debug(f"No ownership history found for {username}, querying TONAPI")

            # Step 1: Get account address from tonapi.io DNS endpoint
            dns_url = f"https://tonapi.io/v2/dns/{username}.t.me"

            async with aiohttp.ClientSession() as session:
                async with session.get(dns_url) as response:
                    if response.status != 200:
                        logger.warning(
                            f"Failed to get DNS info from TONAPI: {response.status}"
                        )
                        logger.debug(f"DNS response for {username}: {response.text}")
                        return None

                    dns_data = await response.json()
                    logger.debug(f"DNS response for {username}: {dns_data}")

                    # Extract address from the response
                    if "item" in dns_data and "address" in dns_data["item"]:
                        address = dns_data["item"]["address"]
                        logger.debug(f"Found address for {username}: {address}")

                        # Step 2: Use address to get auction config
                        auction_url = f"https://tonapi.io/v2/blockchain/accounts/{address}/methods/get_telemint_auction_config"
                        logger.debug(f"Requesting auction config from: {auction_url}")

                        async with session.get(auction_url) as auction_response:
                            if auction_response.status != 200:
                                logger.warning(
                                    f"Failed to get auction config from TONAPI: {auction_response.status}"
                                )
                                return None

                            auction_data = await auction_response.json()

                            # Log the full response for debugging
                            logger.debug(
                                f"Auction config for {username}: {auction_data}"
                            )

                            # Check if we have the expected format
                            if (
                                "decoded" in auction_data
                                and "beneficiar" in auction_data["decoded"]
                            ):
                                beneficiary = auction_data["decoded"]["beneficiar"]

                                # Check if it's a Fragment mint based on the beneficiary address
                                fragment_mint = beneficiary == FRAGMENT_MINT_ADDRESS

                                # Log whether it's a Fragment mint or not
                                if fragment_mint:
                                    logger.debug(
                                        f"Auction for {username} is a Fragment mint"
                                    )
                                else:
                                    logger.debug(
                                        f"Auction for {username} is from owner: {beneficiary}"
                                    )

                            return {"address": address, "auction_config": auction_data}
                    else:
                        logger.warning(
                            f"Address not found in TONAPI DNS response for {username}"
                        )

        return None

    except Exception as e:
        logger.error(f"Error fetching auction config from TONAPI: {str(e)}")
        return None


async def handle_query(inline_query, query: str, user_id: int):
    try:
        # Add a delay before processing
        await asyncio.sleep(FRAGMENT_API_REQUEST_DELAY)

        html_text = await get_fragment_page(query)

        if not html_text:
            short_message = get_status_message("Unavailable", query)
            return await inline_query.answer(
                results=[
                    InlineQueryResultArticle(
                        id="result",
                        title=short_message.replace("*", ""),
                        description=f"Fragment information for @{query}",
                        input_message_content=InputTextMessageContent(
                            message_text=short_message,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True,
                        ),
                        thumbnail_url=FRAGMENT_THUMBNAIL_URL,
                    )
                ],
                cache_time=UNAVAILABLE_USERNAME_CACHE_TIME,
            )

        soup = BeautifulSoup(html_text, "html.parser")
        keyboard_rows = []  # Will contain rows of buttons

        status = await get_username_status(soup)
        if not status:
            return await inline_query.answer(
                results=[error_checking_username_article(query)],
                cache_time=ERROR_CACHE_TIME,
            )

        short_message = get_status_message(status, query)
        long_message = short_message.replace(query, escape_markdown(query))

        if status == "Available":
            available_price = available_price_info(soup, query)
            if available_price:
                keyboard_rows.append([available_price])  # Add as a row with one button

        elif status == "On auction":

            minimum_bid_info = extract_minimum_bid_info(soup, query)
            if minimum_bid_info:
                keyboard_rows.append([minimum_bid_info])

            highest_bid_info = extract_highest_bid_info(soup, query)
            if highest_bid_info:
                keyboard_rows.append([highest_bid_info])

            buy_now_info = extract_buy_now_info(soup, query)
            if buy_now_info:
                keyboard_rows.append([buy_now_info])

            # Get wallet info as a separate row
            wallet_info = most_recent_wallet_info(soup, (not minimum_bid_info))
            if wallet_info:
                keyboard_rows.append(wallet_info)

            tonapi_data = await fetch_auction_config_from_tonapi(query, html_text)

            if tonapi_data:
                # Use the enhanced auction source button
                mint_button = await create_enhanced_auction_source_button(tonapi_data)
                if mint_button:
                    keyboard_rows.append([mint_button])

        elif status == "Sold":
            sold_price = extract_sold_price_info(soup, query)
            if sold_price:
                keyboard_rows.append([sold_price])

            sold_owner = extract_sold_owner_info(soup)
            if sold_owner:
                keyboard_rows.append(sold_owner)

        elif status == "For sale":
            for_sale_owner_info = extract_for_sale_owner_info(soup)
            if for_sale_owner_info:
                keyboard_rows.append(for_sale_owner_info)

            buy_now_info = extract_buy_now_info(soup, query)
            if buy_now_info:
                keyboard_rows.append([buy_now_info])

        if status == "On auction" and minimum_bid_info:
            long_message += " *without* bids"
        elif status == "On auction":
            long_message += " *with* bids"

        if status in ["On auction", "For sale"]:
            ends_in_info = extract_ends_in_info(soup)
            if ends_in_info:
                long_message += f"\n⏱️ Ends in: *{ends_in_info}*"

        reply_markup = None
        if keyboard_rows:
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

        return await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    id="result",
                    title=short_message.replace("*", ""),
                    description=f"Fragment information for @{query}",
                    input_message_content=InputTextMessageContent(
                        message_text=long_message,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True,
                    ),
                    reply_markup=reply_markup,
                    thumbnail_url=FRAGMENT_THUMBNAIL_URL,
                )
            ],
            cache_time=USERNAME_RESULT_CACHE_TIME,
        )

    except Exception as e:
        logger.error(f"Error checking Fragment: {str(e)}")
        return await inline_query.answer(
            results=[error_checking_username_article(query)],
            cache_time=ERROR_CACHE_TIME,
        )
