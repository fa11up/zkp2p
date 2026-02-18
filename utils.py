"""Utility functions for ZKP2P Monitor v2"""


def wei_to_rate(wei_value) -> float:
    """Convert wei (18 decimals) to decimal rate"""
    try:
        return int(wei_value) / 1e18
    except (ValueError, TypeError):
        return 0.0


def format_usdc(amount: int, decimals: int = 6) -> float:
    """Convert raw USDC amount to decimal"""
    return amount / (10 ** decimals)


def is_buy_opportunity(rate: float, target: float) -> bool:
    """Rate below target = buying USDC at a discount"""
    return 0 < rate <= target


def is_sell_opportunity(rate: float, target: float) -> bool:
    """Rate above target = selling USDC at a premium"""
    return rate >= target


def calculate_profit(amount_usd: float, rate: float) -> float:
    """Dollar profit from arbitrage on a given amount and rate"""
    return abs(amount_usd * (rate - 1.0))


def calculate_profit_pct(rate: float) -> float:
    """Profit percentage from rate deviation"""
    return abs((rate - 1.0) * 100)


def short_address(addr: str, chars: int = 6) -> str:
    """Shorten an Ethereum address for display"""
    if not addr or len(addr) < chars * 2:
        return addr or "?"
    return f"{addr[:chars]}...{addr[-4:]}"
