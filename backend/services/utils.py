import os

EXCHANGE = os.getenv("EXCHANGE", "BINGX").upper()
BINGX_BASE_URL = os.getenv("BINGX_BASE_URL", "https://open-api.bingx.com")
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "NEARUSDT")
DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "1m")
CANDLES_LIMIT = int(os.getenv("CANDLES_LIMIT", "500"))

