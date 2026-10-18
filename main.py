import asyncio
import os
import shutil
import sys
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# --- SELF-HEALING FLAT UPLOAD FIX ---
_app_root = os.path.dirname(os.path.abspath(__file__))

# 1. Auto-create 'agents' folder if files were uploaded to root
_agents_dir = os.path.join(_app_root, "agents")
os.makedirs(_agents_dir, exist_ok=True)
_agent_files = ["__init__.py", "base_agent.py", "layer1_market.py", "layer2_tech.py", 
                "layer3_macro.py", "layer4_strategy.py", "layer5_master.py"]
for _af in _agent_files:
    _src = os.path.join(_app_root, _af)
    _dst = os.path.join(_agents_dir, _af)
    if os.path.exists(_src) and not os.path.exists(_dst):
        try:
            shutil.copy2(_src, _dst)
        except Exception:
            pass

# 2. Auto-create 'static' folder if files were uploaded to root
_static_dir = os.path.join(_app_root, "static")
os.makedirs(_static_dir, exist_ok=True)
_static_files = ["index.html", "app.js", "style.css"]
for _sf in _static_files:
    _src = os.path.join(_app_root, _sf)
    _dst = os.path.join(_static_dir, _sf)
    if os.path.exists(_src) and not os.path.exists(_dst):
        try:
            shutil.copy2(_src, _dst)
        except Exception:
            pass

from config import BASE_DIR, UPSTOX_CONFIG
from engine import TradingEngine
from news_feed import market_news_service

# Initialize orchestrator engine
engine = TradingEngine()
background_task_handle = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform initial scan on startup
    logger = engine.data_feed.get_market_pulse()
    print("Initializing 15-AI-Agent NSE Trading System...")
    # Run initial scan in background thread so server starts promptly
    asyncio.create_task(asyncio.to_thread(engine.run_full_scan))
    yield
    engine.auto_scan_active = False

app = FastAPI(
    title="NSE 15-AI-Agent Trading Terminal",
    description="Multi-agent institutional setup generator for Intraday & F&O",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "NSE 15-Agent Trading Terminal Backend is running."}

@app.get("/api/status")
def get_status():
    return {
        "status": "ONLINE",
        "is_scanning": engine.is_scanning,
        "auto_scan_active": engine.auto_scan_active,
        "last_scan_time": engine.last_scan_time,
        "active_setups_count": len(engine.active_setups),
        "approved_count": sum(1 for s in engine.active_setups if s.get("status") == "APPROVED"),
        "watchlist_size": len(engine.watchlist)
    }

@app.get("/api/pulse")
def get_market_pulse():
    pulse = engine.market_pulse or engine.data_feed.get_market_pulse()
    return pulse

@app.get("/api/setups")
def get_setups(filter_approved_only: bool = False):
    setups = engine.active_setups
    if filter_approved_only:
        setups = [s for s in setups if s.get("status") == "APPROVED"]
    return {
        "count": len(setups),
        "last_scan": engine.last_scan_time,
        "setups": setups
    }

@app.get("/api/agents")
def get_agents():
    return {
        "total_agents": 15,
        "agents": engine.get_agent_states()
    }

@app.get("/api/smc-strategies")
def get_smc_strategies():
    return engine.get_smc_strategy_setups()

@app.get("/api/backtest")
def get_backtest_report(timeframe: Optional[str] = None):
    return engine.get_backtest_report(timeframe=timeframe)

@app.get("/api/news")
def get_live_news():
    """Returns live financial market news and sentiment breakdown."""
    overview = market_news_service.get_macro_overview()
    news_items = market_news_service.fetch_news()
    return {
        "status": "SUCCESS",
        "overview": overview,
        "news": news_items
    }

@app.get("/api/chart/{symbol}")
def get_symbol_chart(symbol: str, timeframe: Optional[str] = None):
    """
    Returns candlestick chart data along with strategy-specific logic overlay lines
    (Entry, Stop Loss, Target, CPR levels, FVG bounds, Order Block zones, etc.)
    """
    sym = symbol.strip().upper()
    if not sym.endswith(".NS") and not sym.startswith("^"):
        sym = f"{sym}.NS"
    tf = (timeframe or engine.current_timeframe).lower()

    chart_data = engine.data_feed.get_candles_for_chart(sym, interval=tf, limit=60)
    if not chart_data:
        raise HTTPException(status_code=404, detail=f"No candle data available for {sym}")

    clean_code = sym.replace(".NS", "")

    # 1. Match from active SMC Institutional Strategies
    active_strat = None
    for s_key, s_list in engine.smc_strategy_setups.items():
        for s in s_list:
            if s.get("symbol", "").replace(".NS", "") == clean_code or s.get("symbol") == sym:
                active_strat = s
                break
        if active_strat:
            break

    # 2. Match from High-Conviction Setups ticket
    ticket_setup = None
    for ticket in engine.active_setups:
        if ticket.get("symbol", "").replace(".NS", "") == clean_code or ticket.get("symbol") == sym:
            ticket_setup = ticket
            break

    # 3. If not in cached watchlist, run on-demand live 15-agent evaluation!
    if not active_strat and not ticket_setup:
        try:
            pulse = engine.data_feed.get_market_pulse()
            live_ticket = engine.scan_single_symbol(sym, pulse, timeframe=tf)
            if live_ticket and live_ticket.get("status") == "APPROVED":
                ticket_setup = live_ticket
                smc_res = live_ticket.get("smc_strategies", {})
                for k, v in smc_res.items():
                    if v:
                        active_strat = v
                        break
        except Exception as e:
            print(f"On-demand evaluation note for {sym}: {e}")

    has_active_signal = (active_strat is not None) or (ticket_setup is not None and ticket_setup.get("status") == "APPROVED")

    # 4. Match from breaking news
    news_info = market_news_service.get_news_sentiment_for_symbol(sym)

    # 5. Compute 100-trade backtest specifically for this stock on its active strategy
    strat_name = active_strat.get("strategy_name", "Smart Money Concept") if active_strat else "Smart Money Concept"
    stock_backtest = engine.backtester.backtest_single_stock_strategy(
        symbol=clean_code,
        strategy_name=strat_name,
        ltp=chart_data["ltp"],
        timeframe=tf
    )

    return {
        "status": "SUCCESS",
        "symbol": sym,
        "clean_symbol": clean_code,
        "timeframe": tf.upper(),
        "ltp": chart_data["ltp"],
        "change_pct": chart_data["change_pct"],
        "prev_close": chart_data["prev_close"],
        "indicators": chart_data["indicators"],
        "candles": chart_data["candles"],
        "has_active_signal": has_active_signal,
        "strategy_setup": active_strat,
        "ticket_setup": ticket_setup,
        "news": news_info,
        "stock_backtest": stock_backtest
    }

@app.get("/api/backtest/stock")
def get_stock_backtest(symbol: str, strategy: Optional[str] = "SMC", timeframe: Optional[str] = None):
    """Returns 100-trade backtest scorecard specifically for a single stock."""
    clean_sym = symbol.strip().upper().replace(".NS", "").replace("^", "")
    tf = (timeframe or engine.current_timeframe).lower()
    stock_data = engine.data_feed.get_stock_data(f"{clean_sym}.NS", interval=tf, period="5d")
    ltp = stock_data["ltp"] if stock_data else 1000.0
    return engine.backtester.backtest_single_stock_strategy(
        symbol=clean_sym,
        strategy_name=strategy,
        ltp=ltp,
        timeframe=tf
    )

class TimeframeModel(BaseModel):
    timeframe: str

@app.post("/api/timeframe")
async def set_timeframe(model: TimeframeModel, background_tasks: BackgroundTasks):
    tf = model.timeframe.lower()
    if tf not in ["5m", "15m"]:
        raise HTTPException(status_code=400, detail="Timeframe must be '5m' or '15m'")
    engine.current_timeframe = tf
    background_tasks.add_task(engine.run_full_scan, tf)
    return {"status": "SUCCESS", "current_timeframe": engine.current_timeframe.upper()}

@app.post("/api/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    if engine.is_scanning:
        return {"status": "ALREADY_SCANNING", "message": "A scan is already in progress."}
    background_tasks.add_task(engine.run_full_scan, engine.current_timeframe)
    return {"status": "STARTED", "message": f"Scan triggered on {engine.current_timeframe.upper()} across NSE watchlist."}

@app.get("/api/logs")
def get_logs():
    return {
        "logs": engine.scan_logs
    }

class UpstoxConfigModel(BaseModel):
    api_key: Optional[str] = ""
    api_secret: Optional[str] = ""
    access_token: Optional[str] = ""

@app.get("/api/upstox/config")
def get_upstox_config():
    # Mask secrets
    token = UPSTOX_CONFIG.get("access_token", "")
    masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("Configured" if token else "Not Configured")
    return {
        "is_connected": bool(token),
        "api_key": UPSTOX_CONFIG.get("api_key", ""),
        "access_token_status": masked_token,
        "redirect_uri": UPSTOX_CONFIG.get("redirect_uri", "")
    }

@app.post("/api/upstox/config")
def save_upstox_config(cfg: UpstoxConfigModel):
    if cfg.api_key:
        UPSTOX_CONFIG["api_key"] = cfg.api_key
    if cfg.api_secret:
        UPSTOX_CONFIG["api_secret"] = cfg.api_secret
    if cfg.access_token:
        UPSTOX_CONFIG["access_token"] = cfg.access_token
    return {
        "status": "SUCCESS",
        "message": "Upstox configuration updated successfully.",
        "is_connected": bool(UPSTOX_CONFIG.get("access_token"))
    }

class SettingsModel(BaseModel):
    scan_interval: Optional[int] = None
    watchlist: Optional[List[str]] = None
    auto_scan: Optional[bool] = None

@app.post("/api/settings")
def update_settings(settings: SettingsModel):
    if settings.scan_interval:
        engine.scan_interval = max(15, settings.scan_interval)
    if settings.watchlist:
        engine.watchlist = settings.watchlist
    if settings.auto_scan is not None:
        engine.auto_scan_active = settings.auto_scan
        if engine.auto_scan_active:
            asyncio.create_task(engine.background_scan_loop())
    return {
        "status": "UPDATED",
        "scan_interval": engine.scan_interval,
        "auto_scan_active": engine.auto_scan_active,
        "watchlist": engine.watchlist
    }

# ==================== ALL 2605 NSE STOCKS SEARCH & ANALYZE API ====================
ALL_STOCKS_DB = []
try:
    all_stocks_path = os.path.join(BASE_DIR, "nse_all_stocks.json")
    if os.path.exists(all_stocks_path):
        with open(all_stocks_path, "r", encoding="utf-8") as f:
            ALL_STOCKS_DB = json.load(f)
except Exception as e:
    print(f"Error loading stock database: {e}")

@app.get("/api/stocks/all")
def get_all_stocks_count():
    return {
        "total_listed_stocks": len(ALL_STOCKS_DB),
        "pools_available": ["NIFTY_500", "ALL_NSE_2600", "NSE_FNO_80", "NIFTY_50", "TOP_15"]
    }

@app.get("/api/stocks/search")
def search_stocks(q: str = ""):
    query = q.strip().upper()
    if not query:
        return {"results": []}
    matches = []
    for item in ALL_STOCKS_DB:
        code = item.get("code", "")
        name = item.get("name", "")
        if query in code or query in name.upper():
            matches.append(item)
            if len(matches) >= 30:
                break
    return {"query": query, "count": len(matches), "results": matches}

class AnalyzeStockModel(BaseModel):
    symbol: str

@app.post("/api/stocks/analyze")
def analyze_single_stock(model: AnalyzeStockModel):
    sym = model.symbol.strip().upper()
    if not sym.endswith(".NS") and not sym.startswith("^"):
        sym = f"{sym}.NS"
    ticket = engine.scan_single_symbol(sym, engine.market_pulse, timeframe=engine.current_timeframe)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Stock data not available for symbol '{sym}'")
    return {"status": "SUCCESS", "ticket": ticket}

class WatchlistActionModel(BaseModel):
    symbol: str

@app.post("/api/watchlist/add")
def add_to_watchlist(model: WatchlistActionModel):
    sym = model.symbol.strip().upper()
    if not sym.endswith(".NS") and not sym.startswith("^"):
        sym = f"{sym}.NS"
    if sym not in engine.watchlist:
        engine.watchlist.insert(0, sym)
    return {"status": "SUCCESS", "message": f"{sym} added to active scanner.", "watchlist_count": len(engine.watchlist)}

class WatchlistPoolModel(BaseModel):
    pool: str

@app.get("/api/watchlist")
def get_watchlist():
    return engine.get_watchlist_status()

@app.post("/api/watchlist/pool")
async def switch_watchlist_pool(model: WatchlistPoolModel, background_tasks: BackgroundTasks):
    res = engine.set_watchlist_pool(model.pool)
    if res.get("status") == "SUCCESS":
        background_tasks.add_task(engine.run_full_scan, engine.current_timeframe)
        return res
    raise HTTPException(status_code=400, detail="Invalid watchlist pool. Choose 'ALL_NSE_2600', 'NIFTY_500', 'NSE_FNO_80', 'NIFTY_50', or 'TOP_15'")


# ==================== AUTO-TRADER (UPSTOX & ₹20,000 CAPITAL) ENDPOINTS ====================
class AutoTradeConfigModel(BaseModel):
    is_auto_trade_enabled: Optional[bool] = None
    mode: Optional[str] = None  # 'PAPER' or 'LIVE'
    total_capital: Optional[float] = None
    risk_per_trade_pct: Optional[float] = None
    max_daily_loss: Optional[float] = None
    min_consensus_required: Optional[float] = None

@app.get("/api/autotrade")
def get_autotrade_state():
    return engine.auto_trader.get_all_trades()

@app.post("/api/autotrade/config")
def set_autotrade_config(cfg: AutoTradeConfigModel):
    payload = {}
    if cfg.is_auto_trade_enabled is not None:
        payload["is_auto_trade_enabled"] = cfg.is_auto_trade_enabled
    if cfg.mode is not None:
        payload["mode"] = cfg.mode.upper()
    if cfg.total_capital is not None:
        payload["total_capital"] = cfg.total_capital
    if cfg.risk_per_trade_pct is not None:
        payload["risk_per_trade_pct"] = cfg.risk_per_trade_pct
    if cfg.max_daily_loss is not None:
        payload["max_daily_loss"] = cfg.max_daily_loss
    if cfg.min_consensus_required is not None:
        payload["min_consensus_required"] = cfg.min_consensus_required

    updated_status = engine.auto_trader.update_config(payload)
    return {
        "status": "SUCCESS",
        "message": "Auto-trader settings updated successfully.",
        "config": updated_status
    }

@app.post("/api/autotrade/toggle")
def toggle_autotrade():
    engine.auto_trader.is_auto_trade_enabled = not engine.auto_trader.is_auto_trade_enabled
    return {
        "status": "SUCCESS",
        "is_auto_trade_enabled": engine.auto_trader.is_auto_trade_enabled,
        "mode": engine.auto_trader.mode
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
