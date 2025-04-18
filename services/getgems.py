import json
import time
import asyncio
from typing import Dict, Tuple, Optional

import aiohttp
from loguru import logger

from config import FLOOR_PRICE_CACHE_DURATION, GETGEMS_COLLECTION_ADDRESS
from services.rates import convert_ton_to_usd

# Cache for storing the floor price data
floor_price_cache = {
    "price": None,
    "number": None,
    "item_address": None,
    "last_update": 0,
}

# Cache duration moved to config.py
# CACHE_DURATION = 300

# GetGems GraphQL API endpoint
GETGEMS_API_URL = "https://getgems.io/graphql/"
# GETGEMS_COLLECTION_ADDRESS moved to config.py

# Query parameters in more readable format
QUERY_PARAMS = {
    "operationName": "nftSearch",
    "variables": {
        "query": '{"$and":[{"collectionAddress":"'
        + GETGEMS_COLLECTION_ADDRESS
        + '"},{"saleType":"fix_price"}]}',
        "attributes": None,
        "sort": '[{"fixPrice":{"order":"asc"}},{"index":{"order":"asc"}}]',
        "count": 1,
    },
    "extensions": {
        "persistedQuery": {
            "version": 1,
            "sha256Hash": "0a50a6e37a860bc3a75f3318946b487bbeedd57febc690c0b5b9ddd2302604af",
        }
    },
}


async def fetch_floor_price() -> Optional[Dict]:
    """
    Fetch the floor price from GetGems API
    Returns the first (lowest price) item's details
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
        "Alt-Used": "getgems.io",
        "Priority": "u=4",
        "x-gg-client": "v:1 l:en",
        "content-type": "application/json",
    }

    try:
        # Try POST request instead of GET
        async with aiohttp.ClientSession() as session:
            # First try with POST method (more reliable for GraphQL)

            async with session.post(
                GETGEMS_API_URL, json=QUERY_PARAMS, headers=headers
            ) as response:
                status_code = response.status
                response_text = await response.text()

                # Try to parse response as JSON
                try:
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse GetGems API response: {e}")
                    return None

                if status_code == 200:
                    # Check for errors in the GraphQL response
                    if "errors" in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return None

                    graphql_data = data.get("data", {})
                    if graphql_data == {}:
                        logger.error(
                            "No graphql data found in the GetGems API response"
                        )
                        return None

                    search_results = graphql_data.get("alphaNftItemSearch", {})
                    if search_results == {}:
                        logger.error(
                            "No search results found in the GetGems API response"
                        )
                        return None

                    items = search_results.get("edges", [])

                    # Log full structure if no items found
                    if not items:
                        logger.error("No items found in the GetGems API response")
                        return None

                    if len(items) > 0:
                        first_edge = items[0]
                        first_item = first_edge.get("node", {})

                        if not first_item:
                            logger.error("No node in first edge")
                            return None

                        # Get the number from the name field
                        number = first_item.get("name", "Unknown Number")

                        # Extract the sale information
                        sale_info = first_item.get("sale", {})
                        if sale_info:
                            # Verify the sale type
                            sale_type = sale_info.get("__typename")
                            if sale_type != "NftSaleFixPrice":
                                logger.warning(f"Unexpected sale type: {sale_type}")

                            try:
                                # Extract price in TON (convert from nano TON)
                                price_nano = int(sale_info.get("fullPrice", "0"))
                                price_ton = price_nano / 1_000_000_000

                                # Extract item details
                                item_address = first_item.get("address")

                                return {
                                    "price": price_ton,
                                    "number": number,
                                    "item_address": item_address,
                                }
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error processing sale data: {e}")
                                logger.debug(f"Sale info: {sale_info}")
                        else:
                            logger.error("No sale information found in the first item")
                            logger.debug(f"First item data: {first_item}")
                    else:
                        logger.error("Empty items list in the GetGems API response")
                else:
                    logger.error(f"GetGems API error: Status code {status_code}")

                return None
    except Exception as e:
        logger.error(f"Error fetching GetGems floor price: {e}")
        return None


async def update_floor_price():
    """Update cached floor price from GetGems API"""
    logger.debug("Updating floor price from GetGems API")

    try:
        floor_data = await fetch_floor_price()

        if floor_data:
            floor_price_cache["price"] = floor_data["price"]
            floor_price_cache["number"] = floor_data["number"]
            floor_price_cache["item_address"] = floor_data["item_address"]
            floor_price_cache["last_update"] = time.time()

            logger.info(
                f"Floor price updated: {floor_price_cache['price']} TON for {floor_price_cache['number']}"
            )
        else:
            logger.warning(
                "Could not update floor price, using cached value if available"
            )
    except Exception as e:
        logger.error(f"Error in floor price update: {e}")


async def get_floor_price() -> Tuple[Optional[Dict], int]:
    """
    Get floor price from cache or update if needed
    Returns the floor price data and cache age in seconds
    """
    current_time = time.time()
    cache_age = int(current_time - floor_price_cache["last_update"])

    # Update rates if cache is expired or doesn't exist
    if floor_price_cache["price"] is None or cache_age > FLOOR_PRICE_CACHE_DURATION:
        await update_floor_price()
        cache_age = 0

    return floor_price_cache, cache_age


def create_floor_price_button(item_address: str):
    """Create a button linking to the GetGems item page"""
    if not item_address:
        return None

    url = f"https://getgems.io/collection/{GETGEMS_COLLECTION_ADDRESS}/{item_address}"
    return {"text": "🔍 getgems.io", "url": url}


def create_marketapp_button(item_address: str):
    """Create a button linking to the Market App item page"""
    if not item_address:
        return None

    button_text = f"🛒 marketapp.ws"
    url = f"https://marketapp.ws/{item_address}"

    return {"text": button_text, "url": url}


def format_number_for_telegram(number: str) -> str:
    """
    Format phone number for Telegram URL
    Removes spaces, plus signs, and other non-alphanumeric characters
    """
    # Remove plus sign, spaces, parentheses, and dashes
    formatted = (
        number.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
    )
    return formatted


def create_telegram_number_button(number: str):
    """Create a button linking to the Telegram profile for the number"""
    if not number or number == "Unknown Number":
        return None

    formatted_number = format_number_for_telegram(number)
    url = f"https://t.me/{formatted_number}"
    return {"text": f"📲 {number}", "url": url}


async def get_number_floor_price_message() -> Dict:
    """
    Get the number floor price message for the inline query
    Returns a dictionary with the message and buttons
    """
    # Update floor price data if needed
    floor_data, cache_age = await get_floor_price()

    if not floor_data or floor_data["price"] is None:
        return {
            "title": "Number Floor Price Unavailable",
            "description": "Unable to fetch the current floor price for Fragment numbers",
            "message": "⚠️ *Fragment Numbers Floor Price Unavailable*\n\nUnable to fetch the current floor price for Fragment numbers. Please try again later.",
            "buttons": [],
        }

    # Extract data from the cache
    price_ton = floor_data["price"]
    number = floor_data["number"]
    item_address = floor_data["item_address"]

    price_usd = convert_ton_to_usd(price_ton)
    usd_text = f"(≈ ${price_usd:.2f})" if price_usd else ""

    # Create message content
    title = f"Number Floor Price"
    description = f"💎 {price_ton} TON (≈ ${price_usd:.2f})"

    message = f"📱 *Number Floor Price*\n💎 *{price_ton} TON* {usd_text}\n"

    buttons = []
    if number:
        telegram_button = create_telegram_number_button(number)
        if telegram_button:
            buttons.append([telegram_button])

    if item_address:
        getgems_button = create_floor_price_button(item_address)
        marketapp_button = create_marketapp_button(item_address)

        button_row = [getgems_button]
        if marketapp_button:
            button_row.append(marketapp_button)

        buttons.append(button_row)

    return {
        "title": title,
        "description": description,
        "message": message,
        "buttons": buttons,
    }


async def start_floor_price_update_loop():
    """Start background loop to update floor price periodically"""
    while True:
        try:
            await update_floor_price()
        except Exception as e:
            logger.error(f"Error in floor price update loop: {e}")

        # Wait for next update cycle
        await asyncio.sleep(FLOOR_PRICE_CACHE_DURATION)
