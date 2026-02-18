"""
ZKP2P Monitor v2 — Peerlytics Paid API
=======================================
Monitors for arbitrage opportunities using the Peerlytics v1 API with:
  - Server-side filtering by platform & currency
  - API key authentication & credit tracking
  - Real-time SSE streaming mode
  - Trade execution via signalIntent (with user approval)

Usage:
  python monitor.py                # continuous polling
  MONITOR_MODE=once python monitor.py   # single scan
  MONITOR_MODE=stream python monitor.py # SSE real-time stream
"""

import os
import sys
import time
import json
import threading
from datetime import datetime
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account

from config import (
    RPC_URL,
    CHAIN_ID,
    CONTRACTS,
    ALLOWED_PLATFORMS,
    ALLOWED_CURRENCIES,
    PLATFORM_DISPLAY_NAMES,
    SSE_INTERVAL_MS,
    SSE_EVENT_TYPES,
)
from api_client import PeerlyticsClient
from utils import (
    wei_to_rate,
    is_buy_opportunity,
    is_sell_opportunity,
    calculate_profit,
    calculate_profit_pct,
    short_address,
)

# ─── Orchestrator ABI (signalIntent only) ────────────────────────────────────
ORCHESTRATOR_ABI = [
    {
        "inputs": [
            {"name": "depositId", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
            {"name": "to", "type": "address"},
        ],
        "name": "signalIntent",
        "outputs": [{"name": "intentHash", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]


class ZKP2PMonitor:
    """Monitors ZKP2P deposits for arbitrage opportunities and optionally trades."""

    def __init__(self):
        load_dotenv()

        # ── Settings ──
        self.target_buy = float(os.getenv("TARGET_BUY_RATE", "0.97"))
        self.target_sell = float(os.getenv("TARGET_SELL_RATE", "1.015"))
        self.interval = int(os.getenv("MONITOR_INTERVAL", "60"))
        self.min_amount = float(os.getenv("MIN_AMOUNT_USD", "100"))

        # ── Peerlytics API client ──
        self.api = PeerlyticsClient()

        # ── Web3 / trading ──
        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        self.trading_enabled = False
        self._init_trading()

        self._print_startup()

    # ─────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────────
    def _init_trading(self):
        """Set up wallet + contract if PRIVATE_KEY is in env."""
        pk = os.getenv("PRIVATE_KEY", "").strip()
        if not pk:
            return

        try:
            if not pk.startswith("0x"):
                pk = "0x" + pk
            self.account = Account.from_key(pk)
            self.address = self.account.address
            self.private_key = pk

            orch_addr = Web3.to_checksum_address(CONTRACTS["Orchestrator"])
            self.orchestrator = self.w3.eth.contract(address=orch_addr, abi=ORCHESTRATOR_ABI)
            self.trading_enabled = True
        except Exception as e:
            print(f"⚠️  Could not init trading: {e}")
            print("    Continuing in monitor-only mode...\n")

    def _print_startup(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}")
        print(f"  ZKP2P Monitor v2 — Peerlytics Paid API")
        print(f"  Started: {ts}")
        print(f"{'='*80}")
        print(f"  API Key:  {'✓ configured' if self.api.has_api_key else '✗ missing (set PEERLYTICS_API_KEY in .env)'}")
        print(f"  Web3:     {'✓ connected' if self.w3.is_connected() else '✗ disconnected'}")

        if self.trading_enabled:
            bal = self.w3.eth.get_balance(self.address) / 1e18
            print(f"  Trading:  ✓ enabled")
            print(f"  Wallet:   {self.address}")
            print(f"  Balance:  {bal:.4f} ETH")
        else:
            print(f"  Trading:  ✗ disabled (add PRIVATE_KEY to .env)")

        print(f"\n  Filters:")
        print(f"    Platforms:  {', '.join(ALLOWED_PLATFORMS)}")
        print(f"    Currencies: {', '.join(ALLOWED_CURRENCIES)}")
        print(f"    Min Amount: ${self.min_amount:,.2f}")
        print(f"\n  Targets:")
        print(f"    Buy:  ≤ ${self.target_buy:.4f} ({(1 - self.target_buy)*100:.2f}% discount)")
        print(f"    Sell: ≥ ${self.target_sell:.4f} ({(self.target_sell - 1)*100:.2f}% premium)")
        print(f"{'='*80}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # Data fetching (API v1)
    # ─────────────────────────────────────────────────────────────────────────
    def fetch_deposits(self) -> list:
        """Fetch active, accepting deposits filtered server-side by platform & currency."""
        all_deposits = []
        offset = 0
        limit = 100

        while True:
            resp = self.api.get_deposits(
                status="ACTIVE",
                limit=limit,
                offset=offset,
            )

            # Response shape: {success: bool, data: {deposits: [...], hasMore: bool, ...}}
            inner = resp.get("data", resp) if isinstance(resp, dict) else resp
            if isinstance(inner, dict):
                deposits = inner.get("deposits", [])
                has_more = inner.get("hasMore", False)
            elif isinstance(inner, list):
                deposits = inner
                has_more = False
            else:
                break

            if not deposits:
                break

            all_deposits.extend(deposits)

            if not has_more or len(deposits) < limit:
                break

            offset += limit

        return all_deposits

    def fetch_market_summary(self) -> dict:
        """Fetch market summary with rates for our platforms/currencies."""
        try:
            return self.api.get_market_summary(
                platforms=ALLOWED_PLATFORMS,
                currencies=ALLOWED_CURRENCIES,
                include_rates=True,
            )
        except Exception as e:
            print(f"  ⚠️  Market summary unavailable: {e}")
            return {}

    # ─────────────────────────────────────────────────────────────────────────
    # Opportunity extraction
    # ─────────────────────────────────────────────────────────────────────────
    def extract_opportunities(self, deposits: list) -> dict:
        """Parse deposits into buy/sell opportunity lists, sorted by profit.

        API response fields per deposit:
          availableUsd        – float, already in USD
          depositId           – str (numeric on-chain id)
          depositor           – address
          successRateBps      – int, basis points (10000 = 100%)
          totalIntents        – int
          remainingDeposits   – str (raw USDC amount, 6 decimals)
          intentAmountMin/Max – str (raw USDC)
          markets[]           – [{platform, currency, rate, ...}]
        """
        opps = {"buy": [], "sell": []}

        for dep in deposits:
            available_usd = dep.get("availableUsd", 0)
            if not available_usd or available_usd < self.min_amount:
                continue

            deposit_id = dep.get("depositId", dep.get("id", "?"))
            maker = dep.get("depositor", "")
            success_bps = dep.get("successRateBps", 0)
            success_rate = success_bps / 10000 if success_bps else 0
            total_intents = dep.get("totalIntents", 0)

            # Use the pre-parsed `markets` array
            # Each entry: {platform: "Wise", currency: "USD", rate: 1.0, ...}
            markets = dep.get("markets", [])
            if not markets:
                continue

            for mkt in markets:
                platform = mkt.get("platform", "")
                currency = mkt.get("currency", "")
                rate = mkt.get("rate", 0)

                if not rate or rate <= 0:
                    continue

                profit_usd = calculate_profit(available_usd, rate)
                profit_pct = calculate_profit_pct(rate)
                print(f"Profit: {profit_usd} {profit_pct}")

                opp = {
                    "deposit_id": deposit_id,
                    "rate": rate,
                    "currency": currency,
                    "available_usd": available_usd,
                    "profit_usd": profit_usd,
                    "profit_pct": profit_pct,
                    "platforms": [platform],
                    "maker": maker,
                    "success_rate": success_rate,
                    "total_intents": total_intents,
                    "remaining_raw": dep.get("remainingDeposits", 0),
                    "intent_min": dep.get("intentAmountMin", 0),
                    "intent_max": dep.get("intentAmountMax", 0),
                }

                if is_buy_opportunity(rate, self.target_buy):
                    opp["type"] = "BUY"
                    opp["discount_pct"] = (1.0 - rate) * 100
                    opps["buy"].append(opp)

                if is_sell_opportunity(rate, self.target_sell):
                    opp["type"] = "SELL"
                    opp["premium_pct"] = (rate - 1.0) * 100
                    opps["sell"].append(opp)

        opps["buy"].sort(key=lambda x: x["profit_usd"], reverse=True)
        opps["sell"].sort(key=lambda x: x["profit_usd"], reverse=True)
        return opps

    # ─────────────────────────────────────────────────────────────────────────
    # Display
    # ─────────────────────────────────────────────────────────────────────────
    def display_opportunities(self, opps: dict):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*80}")
        print(f"  Arbitrage Scan — {ts}")
        if self.api.credits_remaining:
            print(f"  API Credits: {self.api.credit_status()}")
        print(f"{'='*80}\n")

        if opps["buy"]:
            print(f"  💰 BUY OPPORTUNITIES (discount ≥ {(1-self.target_buy)*100:.2f}%)")
            print(f"     Sorted by profit\n")
            for i, opp in enumerate(opps["buy"], 1):
                self._print_opp(opp, i)
        else:
            print(f"  No buy opportunities at rate ≤ ${self.target_buy:.4f}\n")

        if opps["sell"]:
            print(f"  💸 SELL OPPORTUNITIES (premium ≥ {(self.target_sell-1)*100:.2f}%)")
            print(f"     Sorted by profit\n")
            for i, opp in enumerate(opps["sell"], 1):
                self._print_opp(opp, i)
        else:
            print(f"  No sell opportunities at rate ≥ ${self.target_sell:.4f}\n")

        print(f"{'='*80}\n")

    def _print_opp(self, opp: dict, rank: int):
        plat_str = ", ".join(
            PLATFORM_DISPLAY_NAMES.get(p.lower(), p) for p in opp["platforms"]
        ) or "—"

        print(f"    #{rank}  Deposit {opp['deposit_id']}")
        print(f"        💵 PROFIT: ${opp['profit_usd']:,.2f} ({opp['profit_pct']:.2f}%)")
        print(f"        Rate: {opp['rate']:.6f} {opp['currency']}")
        print(f"        Available: ${opp['available_usd']:,.2f}")
        print(f"        Payment: {plat_str}")
        if opp["success_rate"]:
            sr = opp["success_rate"]
            sr_pct = sr * 100 if sr <= 1 else sr
            print(f"        Maker: {short_address(opp['maker'])} "
                  f"(success {sr_pct:.0f}%, {opp['total_intents']} intents)")
        print()

    def display_market_summary(self, market: dict):
        if not market:
            return
        # The response shape may vary; display what we can
        summary = market if isinstance(market, dict) else {}
        items = summary.get("data", summary.get("items", summary.get("markets", [])))

        if isinstance(items, list) and items:
            print(f"  📊 Market Rates:")
            for m in items[:10]:
                plat = m.get("platform", m.get("name", "?"))
                curr = m.get("currency", "?")
                rate = m.get("rate", m.get("conversionRate", "?"))
                liq = m.get("liquidity", m.get("availableLiquidity", "?"))
                print(f"     {plat}/{curr}: rate={rate}  liquidity=${liq}")
            print()

    # ─────────────────────────────────────────────────────────────────────────
    # Trade execution
    # ─────────────────────────────────────────────────────────────────────────
    def signal_intent(self, deposit_id: int, amount_usdc: float, recipient: str = None):
        """Send signalIntent transaction on-chain."""
        if not self.trading_enabled:
            print("  ✗ Trading not enabled. Add PRIVATE_KEY to .env")
            return None

        amount_wei = int(amount_usdc * 1e6)
        recipient = Web3.to_checksum_address(recipient or self.address)

        print(f"\n{'='*80}")
        print(f"  Signaling Intent")
        print(f"{'='*80}")
        print(f"  Deposit ID: {deposit_id}")
        print(f"  Amount:     {amount_usdc:,.2f} USDC")
        print(f"  Recipient:  {recipient}")

        try:
            tx = self.orchestrator.functions.signalIntent(
                deposit_id, amount_wei, recipient
            ).build_transaction({
                "from": self.address,
                "nonce": self.w3.eth.get_transaction_count(self.address),
                "gas": 0,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": CHAIN_ID,
            })

            try:
                gas_est = self.w3.eth.estimate_gas(tx)
                tx["gas"] = int(gas_est * 1.2)
                gas_cost = (tx["gas"] * tx["gasPrice"]) / 1e18
                print(f"  Gas:        {tx['gas']:,} (~{gas_cost:.6f} ETH)")
            except Exception as e:
                print(f"  ⚠️  Gas estimation failed: {e}")
                print(f"  Transaction would likely fail.")
                return None

            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            print(f"\n  Sending transaction...")
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction).hex()
            print(f"  ✓ Sent: https://basescan.org/tx/{tx_hash}")

            print(f"  Waiting for confirmation...")
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            if receipt["status"] == 1:
                intent_hash = None
                try:
                    logs = self.orchestrator.events.IntentSignaled().process_receipt(receipt)
                    if logs:
                        intent_hash = logs[0]["args"]["intentHash"].hex()
                except Exception:
                    pass

                print(f"  ✓ Confirmed in block {receipt['blockNumber']}")
                if intent_hash:
                    print(f"  Intent Hash: {intent_hash}")
                print(f"\n  Next steps:")
                print(f"  1. Send fiat payment via the specified method")
                print(f"  2. Generate proof using PeerAuth")
                print(f"  3. Submit proof to complete the intent")
                print(f"  Monitor at: https://zkp2p.xyz\n")

                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "intent_hash": intent_hash,
                    "block": receipt["blockNumber"],
                    "gas_used": receipt["gasUsed"],
                }
            else:
                print(f"  ✗ Transaction reverted!")
                return {"success": False, "tx_hash": tx_hash}

        except Exception as e:
            print(f"  ✗ Error: {e}")
            return {"success": False, "error": str(e)}

    def prompt_for_trade(self, opps: dict) -> bool:
        """Interactive prompt to execute a trade."""
        if not self.trading_enabled:
            return False
        if not (opps["buy"] or opps["sell"]):
            return False

        print(f"  💡 Trade Execution Available")
        print(f"     'buy N'  — execute buy opportunity #N")
        print(f"     'sell N' — execute sell opportunity #N")
        print(f"     'skip'   — continue monitoring")
        print(f"     'exit'   — stop\n")

        try:
            choice = input("  Your choice: ").strip().lower()

            if choice in ("skip", ""):
                return False
            if choice == "exit":
                print("\n  ✋ Exiting...")
                sys.exit(0)

            parts = choice.split()
            if len(parts) != 2 or parts[0] not in ("buy", "sell"):
                print("  ✗ Use 'buy 1' or 'sell 2'")
                return False

            action = parts[0]
            try:
                idx = int(parts[1]) - 1
            except ValueError:
                print("  ✗ Invalid number")
                return False

            opp_list = opps[action]
            if idx < 0 or idx >= len(opp_list):
                print(f"  ✗ Choose 1–{len(opp_list)}")
                return False

            opp = opp_list[idx]

            # Confirmation
            plat_str = ", ".join(
                PLATFORM_DISPLAY_NAMES.get(p.lower(), p) for p in opp["platforms"]
            )
            print(f"\n  ⚠️  CONFIRM TRADE")
            print(f"  Action:     {action.upper()}")
            print(f"  Deposit:    {opp['deposit_id']}")
            print(f"  Rate:       {opp['rate']:.6f} {opp['currency']}")
            print(f"  Available:  ${opp['available_usd']:,.2f}")
            print(f"  Profit:     ${opp['profit_usd']:,.2f} ({opp['profit_pct']:.2f}%)")
            print(f"  Payment:    {plat_str}")

            amt_input = input(f"\n  Amount (USD) [default: {opp['available_usd']:.2f}]: ").strip()
            amount = opp["available_usd"]
            if amt_input:
                try:
                    amount = float(amt_input)
                    if amount <= 0 or amount > opp["available_usd"]:
                        print(f"  ✗ Must be 0–{opp['available_usd']:.2f}")
                        return False
                except ValueError:
                    print("  ✗ Invalid amount")
                    return False

            confirm = input(f"\n  Execute trade for ${amount:,.2f}? (yes/no): ").strip().lower()
            if confirm == "yes":
                self.signal_intent(opp["deposit_id"], amount)
                return True
            else:
                print("  ✗ Cancelled")
                return False

        except KeyboardInterrupt:
            print("\n  ✗ Cancelled")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Run modes
    # ─────────────────────────────────────────────────────────────────────────
    def run_once(self):
        """Single scan."""
        print("  Fetching deposits from Peerlytics API...")
        try:
            deposits = self.fetch_deposits()
        except Exception as e:
            print(f"  ✗ API error: {e}")
            return

        print(f"  Received {len(deposits)} deposits")
        print(deposits)

        opps = self.extract_opportunities(deposits)
        print(opps)

        # Optional: market summary
        try:
            market = self.fetch_market_summary()
            self.display_market_summary(market)
        except Exception:
            pass

        self.display_opportunities(opps)

        total = len(opps["buy"]) + len(opps["sell"])
        print(f"  Found: {len(opps['buy'])} buy, {len(opps['sell'])} sell opportunities")

        if self.trading_enabled and total > 0:
            self.prompt_for_trade(opps)

    def run_continuous(self):
        """Poll at interval."""
        print(f"  🔄 Continuous monitoring (every {self.interval}s)")
        print(f"  Press Ctrl+C to stop\n")
        try:
            while True:
                self.run_once()
                print(f"  ⏱️  Next scan in {self.interval}s...")
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\n\n  ✋ Stopped")
            sys.exit(0)

    def run_stream(self):
        """Real-time SSE stream mode."""
        try:
            import sseclient
        except ImportError:
            print("  ✗ SSE mode requires sseclient-py: pip install sseclient-py")
            print("  Falling back to polling mode...\n")
            self.run_continuous()
            return

        url = self.api.get_activity_stream_url(
            event_types=SSE_EVENT_TYPES,
            interval_ms=SSE_INTERVAL_MS,
        )
        print(f"  📡 Connecting to SSE stream...")
        print(f"  Events: {', '.join(SSE_EVENT_TYPES)}")
        print(f"  Press Ctrl+C to stop\n")

        try:
            import requests as req
            headers = {}
            if self.api.api_key:
                headers["x-api-key"] = self.api.api_key

            resp = req.get(url, stream=True, headers=headers, timeout=None)
            client = sseclient.SSEClient(resp)

            for event in client.events():
                if event.event == "activity":
                    try:
                        data = json.loads(event.data)
                        self._handle_stream_event(data)
                    except json.JSONDecodeError:
                        pass
                elif event.event == "error":
                    print(f"  ⚠️  Stream error: {event.data}")

        except KeyboardInterrupt:
            print("\n\n  ✋ Stream stopped")
            sys.exit(0)
        except Exception as e:
            print(f"  ✗ Stream error: {e}")
            print("  Falling back to polling...\n")
            self.run_continuous()

    def _handle_stream_event(self, event: dict):
        """Process a single SSE activity event."""
        etype = event.get("type", event.get("eventType", "?"))
        ts = datetime.now().strftime("%H:%M:%S")

        if "intent" in etype.lower():
            deposit_id = event.get("depositId", "?")
            amount = event.get("amount", 0)
            owner = event.get("owner", event.get("taker", "?"))
            print(f"  [{ts}] {etype}: deposit={deposit_id} amount={amount} by {short_address(owner)}")

        elif "deposit" in etype.lower():
            deposit_id = event.get("depositId", "?")
            depositor = event.get("depositor", "?")
            print(f"  [{ts}] {etype}: deposit={deposit_id} by {short_address(depositor)}")

        else:
            print(f"  [{ts}] {etype}: {json.dumps(event)[:120]}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    try:
        monitor = ZKP2PMonitor()
        mode = os.getenv("MONITOR_MODE", "continuous").lower()

        if mode == "once":
            monitor.run_once()
        elif mode == "stream":
            monitor.run_stream()
        else:
            monitor.run_continuous()

    except Exception as e:
        print(f"\n  ❌ FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
