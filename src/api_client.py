"""
Peerlytics API v1 Client
Handles authentication, rate limits, and all endpoint calls
"""

import os
import json
import requests
from typing import Optional
from src.config import PEERLYTICS_BASE_URL, ENDPOINTS


class PeerlyticsClient:
    """Client for the Peerlytics paid API (v1)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEERLYTICS_API_KEY", "")
        self.base_url = PEERLYTICS_BASE_URL
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"x-api-key": self.api_key})

        # Track credits from response headers
        self.credits_remaining = None
        self.credits_source = None
        self.rate_limit_remaining = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, params: dict = None, **kwargs) -> dict:
        """Make an authenticated request and track rate/credit headers"""
        resp = self.session.request(method, self._url(path), params=params, timeout=30, **kwargs)

        # Track headers
        self.credits_remaining = resp.headers.get("X-Credits-Remaining")
        self.credits_source = resp.headers.get("X-Credits-Source")
        self.rate_limit_remaining = resp.headers.get("X-RateLimit-Remaining")

        resp.raise_for_status()
        return resp.json()

    def get(self, path: str, params: dict = None) -> dict:
        return self._request("GET", path, params=params)

    # ── Deposits ─────────────────────────────────────────────────────────
    def get_deposits(
        self,
        status: str = "ACTIVE",
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        """
        Query deposits with server-side filtering.
        The API requires at least one filter param.
        """
        params = {"status": status, "limit": limit, "offset": offset}
        return self.get(ENDPOINTS["deposits"], params=params)

    # ── Market ───────────────────────────────────────────────────────────
    def get_market_summary(
        self,
        platforms: list[str] = None,
        currencies: list[str] = None,
        include_rates: bool = True,
        limit: int = 200,
    ) -> dict:
        params = {"includeRates": str(include_rates).lower(), "limit": limit}
        if platforms:
            params["platform"] = platforms
        if currencies:
            params["currency"] = currencies
        return self.get(ENDPOINTS["market_summary"], params=params)

    # ── Explorer ─────────────────────────────────────────────────────────
    def get_deposit_detail(self, deposit_id: str, limit: int = 100) -> dict:
        path = f"{ENDPOINTS['explorer_deposit']}/{deposit_id}"
        return self.get(path, params={"limit": limit})

    def get_intent_detail(self, intent_hash: str) -> dict:
        path = f"{ENDPOINTS['explorer_intent']}/{intent_hash}"
        return self.get(path)

    # ── Activity ─────────────────────────────────────────────────────────
    def get_activity(
        self,
        event_type: str = None,
        since: str = None,
        limit: int = 50,
    ) -> dict:
        params = {"limit": limit}
        if event_type:
            params["type"] = event_type
        if since:
            params["since"] = since
        return self.get(ENDPOINTS["activity"], params=params)

    def get_activity_stream_url(
        self,
        event_types: list[str] = None,
        interval_ms: int = 5000,
    ) -> str:
        """Build the SSE stream URL (for use with sseclient or similar)"""
        url = self._url(ENDPOINTS["activity_stream"])
        parts = [f"intervalMs={interval_ms}"]
        if event_types:
            for t in event_types:
                parts.append(f"type={t}")
        if self.api_key:
            parts.append(f"x-api-key={self.api_key}")  # SSE may need query param auth
        return f"{url}?{'&'.join(parts)}"

    # ── Analytics ─────────────────────────────────────────────────────────
    def get_analytics_summary(self) -> dict:
        return self.get(ENDPOINTS["analytics_summary"])

    # ── Metadata ──────────────────────────────────────────────────────────
    def get_platforms(self) -> dict:
        return self.get(ENDPOINTS["meta_platforms"])

    def get_currencies(self) -> dict:
        return self.get(ENDPOINTS["meta_currencies"])

    # ── Status ────────────────────────────────────────────────────────────
    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    def credit_status(self) -> str:
        if self.credits_remaining is None:
            return "unknown (no requests yet)"
        return f"{self.credits_remaining} remaining ({self.credits_source})"
