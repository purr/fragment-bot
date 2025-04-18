# Fragment Bot

A Telegram inline bot that provides information about Fragment usernames, TON price, and NFT floor prices.

## Features

- Check username availability on Fragment
- Get current TON price
- Convert between TON and USD
- View Floor Price of Fragment Numbers

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your Telegram bot token:
   ```
   BOT_TOKEN=your_telegram_bot_token
   ```

## Running the Bot

Start the bot with:

```
python bot.py
```

## Usage

The bot works in Telegram's inline mode:

- `@YourBot username` - Check username availability on Fragment
- `@YourBot 100` - Convert between TON and USD (works with any number)
- `@YourBot` - Get the current TON price and Number floor price

## Data Sources

- TON price from CoinGecko and Binance
- Fragment username data from fragment.com
- Floor price data from GetGems.io
