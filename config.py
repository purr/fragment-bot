"""
Configuration settings for the Fragment bot.
All configurable parameters are centralized here.
"""

# Cache durations (in seconds)
TON_RATE_CACHE_DURATION = 120  # 2 minutes
FLOOR_PRICE_CACHE_DURATION = 300  # 5 minutes

# API response cache times (in seconds)
EMPTY_QUERY_CACHE_TIME = 5
INVALID_QUERY_CACHE_TIME = 300  # 5 minutes
ERROR_CACHE_TIME = 5
UNAVAILABLE_USERNAME_CACHE_TIME = 300  # 5 minutes
NUMERIC_QUERY_CACHE_TIME = 30
USERNAME_RESULT_CACHE_TIME = 300  # 5 minutes

# GetGems collection configuration
GETGEMS_COLLECTION_ADDRESS = (
    "EQAOQdwdw8kGftJCSFgOErM1mBjYPe4DBPq8-AhF6vr9si5N"  # Fragment collection address
)

# UI Images & Resources
FRAGMENT_THUMBNAIL_URL = "https://storage.getblock.io/web/web/images/marketplace/Fragment/photo_2024-07-23_22-06-50.jpg"
TON_THUMBNAIL_URL = (
    "https://pbs.twimg.com/profile_images/1602985148219260928/VC-Mraev_400x400.jpg"
)

# TON Fragment mint address (used to detect if auction is from Fragment or user)
FRAGMENT_MINT_ADDRESS = (
    "0:408da3b28b6c065a593e10391269baaa9c5f8caebc0c69d9f0aabbab2a99256b"
)

# Price formatting
DEFAULT_DECIMAL_PLACES = 2
TON_DECIMAL_PLACES = 4

# Username validation regex pattern
USERNAME_PATTERN = r"^[a-z][a-z0-9_]{2,}[a-z0-9]$"

# API Request delay
FRAGMENT_API_REQUEST_DELAY = 0.5  # seconds
