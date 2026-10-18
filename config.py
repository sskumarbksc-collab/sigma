import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Top Liquid 15 (Ultra-fast 3-second sweep, ideal for fast 5m scalping)
TOP_LIQUID_15 = [
    "^NSEI",          # NIFTY 50
    "^NSEBANK",       # BANK NIFTY
    "RELIANCE.NS",    # Reliance Industries
    "HDFCBANK.NS",    # HDFC Bank
    "ICICIBANK.NS",   # ICICI Bank
    "INFY.NS",        # Infosys
    "TCS.NS",         # TCS
    "SBIN.NS",        # State Bank of India
    "TATASTEEL.NS",   # Tata Steel
    "BAJFINANCE.NS",  # Bajaj Finance
    "AXISBANK.NS",    # Axis Bank
    "KOTAKBANK.NS",   # Kotak Mahindra Bank
    "LT.NS",          # Larsen & Toubro
    "BHARTIARTL.NS",  # Bharti Airtel
    "ITC.NS"          # ITC
]

# 2. Entire NIFTY 50 (Full benchmark index of India)
NIFTY_50_WATCHLIST = [
    "^NSEI", "^NSEBANK",
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS", "BEL.NS", "BPCL.NS",
    "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "ITC.NS",
    "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS",
    "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS", "ONGC.NS",
    "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS", "SHRIRAMFIN.NS", "SBIN.NS",
    "SUNPHARMA.NS", "TCS.NS", "TATACONSUM.NS", "TMPV.NS", "TATASTEEL.NS",
    "TECHM.NS", "TITAN.NS", "TRENT.NS", "ULTRACEMCO.NS", "WIPRO.NS"
]

# 3. High-Beta NSE F&O Momentum Universe (Top 80 liquid swing & intraday movers)
NSE_FNO_80_WATCHLIST = list(set(NIFTY_50_WATCHLIST + [
    "HAL.NS", "ZOMATO.NS", "DIXON.NS", "POLYCAB.NS", "PERSISTENT.NS",
    "COFORGE.NS", "VEDL.NS", "JINDALSTEL.NS", "FEDERALBNK.NS", "AUROPHARMA.NS",
    "LUPIN.NS", "CHOLAFIN.NS", "MUTHOOTFIN.NS", "CANBK.NS", "BANKBARODA.NS",
    "PNB.NS", "DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "INDIGO.NS",
    "TATAPOWER.NS", "BHEL.NS", "PFC.NS", "RECLTD.NS", "IOC.NS",
    "GAIL.NS", "AMBUJACEM.NS", "ACC.NS", "VOLTAS.NS", "HAVELLS.NS"
]))

# 4. Load NIFTY 500 (501 Liquid Capital Leaders)
NIFTY_500_WATCHLIST = list(NIFTY_50_WATCHLIST)
nifty_500_file = os.path.join(BASE_DIR, "nifty_500_stocks.json")
if os.path.exists(nifty_500_file):
    try:
        with open(nifty_500_file, "r") as f:
            nifty_500_data = json.load(f)
            NIFTY_500_WATCHLIST = [s["symbol"] for s in nifty_500_data]
    except Exception:
        pass

# 5. Load ALL 2,605 NSE Listed Stocks
ALL_NSE_2600_WATCHLIST = list(NIFTY_500_WATCHLIST)
all_nse_file = os.path.join(BASE_DIR, "nse_all_stocks.json")
if os.path.exists(all_nse_file):
    try:
        with open(all_nse_file, "r") as f:
            all_nse_data = json.load(f)
            ALL_NSE_2600_WATCHLIST = [s["symbol"] for s in all_nse_data]
    except Exception:
        pass

# Watchlist Pools dictionary
WATCHLIST_POOLS = {
    "TOP_15": TOP_LIQUID_15,
    "NIFTY_50": NIFTY_50_WATCHLIST,
    "NSE_FNO_80": NSE_FNO_80_WATCHLIST,
    "NIFTY_500": NIFTY_500_WATCHLIST,
    "ALL_NSE_2600": ALL_NSE_2600_WATCHLIST
}

DEFAULT_WATCHLIST = list(NIFTY_50_WATCHLIST) # Default to NIFTY 50 benchmark leaders for instant relevant scanning

# Consensus threshold for a setup to be approved by Agent 14 (Master Arbiter)
MIN_CONSENSUS_THRESHOLD = 0.70

# Scan interval in seconds
DEFAULT_SCAN_INTERVAL = 60

# Upstox API Configuration (Can be updated via UI or environment)
UPSTOX_CONFIG = {
    "api_key": os.getenv("UPSTOX_API_KEY", ""),
    "api_secret": os.getenv("UPSTOX_API_SECRET", ""),
    "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/upstox/callback"),
    "access_token": os.getenv("UPSTOX_ACCESS_TOKEN", "")
}
