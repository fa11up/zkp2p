"""Configuration for ZKP2P Monitor v2 - Peerlytics Paid API"""

# =============================================================================
# Peerlytics API v1
# =============================================================================
PEERLYTICS_BASE_URL = "https://peerlytics.xyz/api/v1"

# Endpoint paths
ENDPOINTS = {
    "deposits": "/deposits",
    "market_summary": "/market/summary",
    "activity": "/activity",
    "activity_stream": "/activity/stream",
    "explorer_deposit": "/explorer/deposit",
    "explorer_intent": "/explorer/intent",
    "meta_platforms": "/meta/platforms",
    "meta_currencies": "/meta/currencies",
    "analytics_summary": "/analytics/summary",
}

# =============================================================================
# QuickNode RPC (for transactions)
# =============================================================================
CHAIN_ID = 8453  # Base
RPC_URL = "https://winter-evocative-panorama.base-mainnet.quiknode.pro/7d3762abcffbbc9b37139e94d8124a17e84c41f9/"

# =============================================================================
# Contract addresses (Base)
# =============================================================================
CONTRACTS = {
    "Escrow": "0x2f121CDDCA6d652f35e8B3E560f9760898888888",
    "Orchestrator": "0x88888883Ed048FF0a415271B28b2F52d431810D0",
}

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6

# =============================================================================
# Filters
# =============================================================================

# Platform IDs (used as ?platform= param in API)
ALLOWED_PLATFORMS = [
    "zelle",
    "paypal",
    "revolut",
    "wise",
]

# Currency codes (used as ?currency= param in API)
ALLOWED_CURRENCIES = [
    "USD",
    "GBP",
    "EUR",
    "CAD",
    "AUD",
]

# Display names for platforms
PLATFORM_DISPLAY_NAMES = {
    "zelle": "Zelle",
    "zelle-citi": "Zelle (Citi)",
    "zelle-chase": "Zelle (Chase)",
    "zelle-bofa": "Zelle (BofA)",
    "paypal": "PayPal",
    "revolut": "Revolut",
    "wise": "Wise",
    "venmo": "Venmo",
    "cashapp": "Cash App",
    "monzo": "Monzo",
    "mercadopago": "Mercado Pago",
    "n26": "N26",
    "chime": "Chime",
}

# =============================================================================
# SSE Stream defaults
# =============================================================================
SSE_INTERVAL_MS = 5000  # 5 seconds between SSE polls
SSE_EVENT_TYPES = [
    "intent_signaled",
    "intent_fulfilled",
    "deposit_created",
    "deposit_rate_updated",
]
