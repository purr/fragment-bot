import time
import asyncio
from typing import Dict, Tuple, Optional

import aiohttp
from loguru import logger

from config import TON_RATE_CACHE_DURATION

# Cache for storing rates
rates_cache = {"ton_usd": None, "last_update": 0, "source1": None, "source2": None}

# Cache duration moved to config.py
# CACHE_DURATION = 120


async def fetch_coingecko_price() -> Optional[float]:
    """Fetch TON price from CoinGecko API"""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get("the-open-network", {}).get("usd")
                    return price
                else:
                    logger.error(f"CoinGecko API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching CoinGecko price: {e}")
        return None


async def fetch_binance_price() -> Optional[float]:
    """Fetch TON price from Binance API"""
    url = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    price = float(data.get("price", 0))
                    return price
                else:
                    logger.error(f"Binance API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching Binance price: {e}")
        return None


async def update_rates():
    """Update cached rates from external sources"""

    # Fetch prices from both sources concurrently
    coingecko_price, binance_price = await asyncio.gather(
        fetch_coingecko_price(), fetch_binance_price(), return_exceptions=True
    )

    # Convert exceptions to None
    if isinstance(coingecko_price, Exception):
        logger.error(f"CoinGecko error: {coingecko_price}")
        coingecko_price = None

    if isinstance(binance_price, Exception):
        logger.error(f"Binance error: {binance_price}")
        binance_price = None

    # Store source prices
    rates_cache["source1"] = coingecko_price
    rates_cache["source2"] = binance_price

    # Calculate average price if both sources are available
    if coingecko_price is not None and binance_price is not None:
        rates_cache["ton_usd"] = (coingecko_price + binance_price) / 2
    # Otherwise use whichever is available
    elif coingecko_price is not None:
        rates_cache["ton_usd"] = coingecko_price
    elif binance_price is not None:
        rates_cache["ton_usd"] = binance_price

    if rates_cache["ton_usd"] is not None:
        rates_cache["ton_usd"] = round(rates_cache["ton_usd"], 4)

    rates_cache["last_update"] = time.time()
    logger.info(f"TON rate updated: 1 TON = {rates_cache['ton_usd']} USD")


async def get_ton_price() -> Tuple[Optional[float], Dict]:
    """Get TON price from cache or update if needed"""
    current_time = time.time()

    # Update rates if cache is expired or doesn't exist
    if (
        rates_cache["ton_usd"] is None
        or (current_time - rates_cache["last_update"]) > TON_RATE_CACHE_DURATION
    ):
        await update_rates()

    # Return the price and source info
    return rates_cache["ton_usd"], {
        "source1": rates_cache["source1"],
        "source2": rates_cache["source2"],
        "last_update": rates_cache["last_update"],
    }


def convert_usd_to_ton(usd_amount: float) -> Optional[float]:
    """Convert USD amount to TON"""
    if rates_cache["ton_usd"] is None or rates_cache["ton_usd"] == 0:
        return None
    return usd_amount / rates_cache["ton_usd"]


def convert_ton_to_usd(ton_amount: float) -> Optional[float]:
    """Convert TON amount to USD"""
    if rates_cache["ton_usd"] is None:
        return None
    return ton_amount * rates_cache["ton_usd"]


async def start_rate_update_loop():
    """Start background loop to update rates every 2 minutes"""
    while True:
        try:
            await update_rates()
        except Exception as e:
            logger.error(f"Error in rate update loop: {e}")

        # Wait for next update cycle
        await asyncio.sleep(TON_RATE_CACHE_DURATION)
