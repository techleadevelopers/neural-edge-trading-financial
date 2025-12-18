import os

EXCHANGE = os.getenv("EXCHANGE", "BINGX").upper()
BINGX_BASE_URL = os.getenv("BINGX_BASE_URL", "https://open-api.bingx.com")
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "NEARUSDT")
DEFAULT_INTERVAL = os.getenv("DEFAULT_INTERVAL", "1m")
CANDLES_LIMIT = int(os.getenv("CANDLES_LIMIT", "500"))

# Lista de origens permitidas para CORS (separadas por virgula)
API_ALLOW_ORIGINS = [
    o.strip()
    for o in os.getenv("API_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

# Controle de cache em segundos para coleta de candles
CANDLES_CACHE_SEC = int(os.getenv("CANDLES_CACHE_SEC", "15"))

# Token opcional para proteger endpoints sensiveis
AUTH_TOKEN = os.getenv("AUTH_TOKEN")

# Requisições externas
HTTP_RETRIES = int(os.getenv("HTTP_RETRIES", "2"))
HTTP_BACKOFF_BASE = float(os.getenv("HTTP_BACKOFF_BASE", "0.6"))

# Regime snapshot cache (para nao bater fontes externas a cada request)
REGIME_SNAPSHOT_TTL_SEC = int(os.getenv("REGIME_SNAPSHOT_TTL_SEC", "120"))
