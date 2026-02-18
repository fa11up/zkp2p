# ZKP2P API Monitor - Arbitrage Opportunity Finder

**Fast, API-based arbitrage opportunity finder for ZKP2P protocol**

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the monitor
python monitor.py
```

That's it! The monitor will start finding profitable opportunities instantly.

## ✨ Features

✅ **Instant Data** - Uses Peerlytics API (no blockchain scanning)  
✅ **Profit Ranked** - Shows highest profit opportunities first  
✅ **Smart Filtering** - Only your preferred payment methods & currencies  
✅ **Maker Stats** - See success rates and reputation  
✅ **Live Updates** - Continuous monitoring with 60s refresh  
✅ **Web3 Ready** - Maintains RPC connection for future transactions  

## 🎯 What You Get

### Buy Opportunities (Discounts)
Get USDC at below $1.00:
- Rate 0.95 = 5% discount = Save $50 per $1,000
- Rate 0.97 = 3% discount = Save $30 per $1,000

### Sell Opportunities (Premiums)
Sell USDC above $1.00:
- Rate 1.03 = 3% premium = Earn $30 per $1,000
- Rate 1.05 = 5% premium = Earn $50 per $1,000

## 📊 Example Output

```
================================================================================
Arbitrage Opportunities - 2026-01-23 12:30:00
================================================================================

📊 Market Summary:
   Total Available Liquidity: $389,885.28
   Locked in Intents: $3,454.91
   Active Deposits: 824
   Your Opportunities: 3 buy, 5 sell

💸 SELL OPPORTUNITIES (Premium ≥ 1.50%)
   Sorted by Highest Profit

  #1 - Deposit ID: 1281
      💵 PROFIT: $709.47 (7.90%)
      Rate: 1.079000 USD
      Available: $8,978.06
      Payment: Venmo, Zelle, Cash App
      Maker: 0xaa8F20c0... (Success: 58%, Intents: 39)

  #2 - Deposit ID: 740
      💵 PROFIT: $300.00 (3.00%)
      Rate: 1.030000 USD
      Available: $10,000.00
      Payment: Revolut
      Maker: 0x88e509AD... (Success: 83%, Intents: 30)

💰 BUY OPPORTUNITIES (Discount ≥ 5.00%)
   Sorted by Highest Profit

  #1 - Deposit ID: 1795
      💵 PROFIT: $50.00 (1.00%)
      Rate: 0.990000 USD
      Available: $4,994.95
      Payment: Zelle
      Maker: 0x425c14B9... (Success: 100%, Intents: 1)

================================================================================
```

## ⚙️ Configuration

Edit `.env`:

```bash
TARGET_BUY_RATE=0.95          # Buy at ≤5% discount
TARGET_SELL_RATE=1.015        # Sell at ≥1.5% premium
MIN_AMOUNT_USD=100            # Minimum deposit size
MONITOR_INTERVAL=60           # Refresh every 60 seconds
MONITOR_MODE=continuous       # or 'once'
```

### Supported Payment Methods
Currently filtering for:
- ✅ Zelle
- ✅ PayPal
- ✅ Revolut
- ✅ Wise

Edit `ALLOWED_PAYMENT_METHODS` in `config.py` to customize.

### Supported Currencies
Currently filtering for:
- ✅ USD
- ✅ GBP
- ✅ EUR
- ✅ CAD
- ✅ AUD

Edit `ALLOWED_CURRENCIES` in `config.py` to customize.

## 🎮 Usage

**Continuous monitoring:**
```bash
python monitor_api.py
```

**Single scan:**
```bash
MONITOR_MODE=once python monitor_api.py
```

**Custom settings:**
```bash
TARGET_BUY_RATE=0.98 TARGET_SELL_RATE=1.01 python monitor_api.py
```

## 📈 Understanding Results

### Conversion Rates
- **1.00** = Par (no profit)
- **0.95** = 5% discount (BUY)
- **1.05** = 5% premium (SELL)

### Profit Calculation
```
Profit = Available Amount × |Rate - 1.00|

Example: $10,000 at 1.03
Profit = $10,000 × 0.03 = $300
```

## 📂 Project Structure

**Main Scripts:**
- `monitor_api.py` ⭐ API-based monitor (recommended)
- `monitor_v2.py` - Blockchain monitor (backup)
- `monitor.py` - Simple monitor (backup)

**Config:**
- `config.py` - Settings
- `utils.py` - Helpers
- `.env` - Your preferences

**Docs:**
- `README.md` - This file
- `API_SYNOPSIS.md` - API overview
- `API_ANALYSIS.md` - API details

## ⚠️ Important

**This monitor is READ-ONLY**
- Shows opportunities ✅
- Calculates profit ✅
- Does NOT execute trades ❌

**To trade:**
1. Visit https://zkp2p.xyz
2. Find deposit by ID
3. Execute manually

## 🔧 Technical Details

**Speed:**
- API method: <1 second
- Blockchain method: 30-60 seconds

**Data Source:**
- Peerlytics API
- Real-time updates
- Exact available amounts

**Web3:**
- QuickNode RPC ready
- For future transaction features
- Currently read-only

## 🎯 Best Practices

**Conservative:**
```
TARGET_BUY_RATE=0.97
TARGET_SELL_RATE=1.03
MIN_AMOUNT_USD=500
```

**Moderate:**
```
TARGET_BUY_RATE=0.95
TARGET_SELL_RATE=1.02
MIN_AMOUNT_USD=100
```

**Aggressive:**
```
TARGET_BUY_RATE=0.98
TARGET_SELL_RATE=1.01
MIN_AMOUNT_USD=50
```

## 📚 Resources

- ZKP2P: https://zkp2p.xyz
- Peerlytics: https://peerlytics.xyz
- Docs: https://docs.zkp2p.xyz

## 📝 License

MIT
