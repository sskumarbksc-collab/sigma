import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("AutoTrader")

# Symbol to Upstox Instrument Token mapping for common liquid NSE stocks
UPSTOX_NSE_EQUITY_TOKENS = {
    "RELIANCE": "NSE_EQ|INE002A01018",
    "RELIANCE.NS": "NSE_EQ|INE002A01018",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "HDFCBANK.NS": "NSE_EQ|INE040A01034",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "ICICIBANK.NS": "NSE_EQ|INE090A01021",
    "INFY": "NSE_EQ|INE009A01021",
    "INFY.NS": "NSE_EQ|INE009A01021",
    "TCS": "NSE_EQ|INE467B01029",
    "TCS.NS": "NSE_EQ|INE467B01029",
    "SBIN": "NSE_EQ|INE062A01020",
    "SBIN.NS": "NSE_EQ|INE062A01020",
    "TATASTEEL": "NSE_EQ|INE081A01020",
    "TATASTEEL.NS": "NSE_EQ|INE081A01020",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "BAJFINANCE.NS": "NSE_EQ|INE296A01024",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "AXISBANK.NS": "NSE_EQ|INE238A01034",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "KOTAKBANK.NS": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "LT.NS": "NSE_EQ|INE018A01030",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "BHARTIARTL.NS": "NSE_EQ|INE397D01024",
    "ITC": "NSE_EQ|INE154A01025",
    "ITC.NS": "NSE_EQ|INE154A01025"
}

class AutoTrader:
    """
    Automated Trading Execution Engine for Upstox API & Paper Trading.
    Tailored for specified capital (Default: ₹20,000).
    Features:
      - Dynamic Position Sizing (Risk 1-1.5% max per trade)
      - Upstox API v2 Order Placement (Intraday MIS)
      - Circuit Breaker: Auto-stops if daily max loss limit hit
      - Paper Trading / Live Broker Toggle
      - Real-time SL/TP order tracking and profit booking
    """

    def __init__(self, initial_capital: float = 20000.0):
        self.total_capital: float = initial_capital
        self.available_capital: float = initial_capital
        self.is_auto_trade_enabled: bool = False
        self.mode: str = "PAPER"  # 'PAPER' or 'LIVE'
        self.risk_per_trade_pct: float = 1.5  # 1.5% of 20,000 = ₹300 max risk
        self.max_daily_loss: float = 1000.0    # 5% of 20,000 circuit breaker
        self.daily_pnl: float = 0.0
        self.min_consensus_required: float = 70.0 # Only trade >= 70% consensus

        # Trade books
        self.open_trades: List[Dict[str, Any]] = []
        self.closed_trades: List[Dict[str, Any]] = []
        self.trade_counter: int = 1

    def update_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Updates auto-trading parameters from frontend UI."""
        if "is_auto_trade_enabled" in config:
            self.is_auto_trade_enabled = bool(config["is_auto_trade_enabled"])
        if "mode" in config and config["mode"] in ["PAPER", "LIVE"]:
            self.mode = config["mode"]
        if "total_capital" in config and config["total_capital"] > 0:
            self.total_capital = float(config["total_capital"])
            self.available_capital = self.total_capital
        if "risk_per_trade_pct" in config:
            self.risk_per_trade_pct = float(config["risk_per_trade_pct"])
        if "max_daily_loss" in config:
            self.max_daily_loss = float(config["max_daily_loss"])
        if "min_consensus_required" in config:
            self.min_consensus_required = float(config["min_consensus_required"])

        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Returns the current auto-trader dashboard state."""
        return {
            "is_auto_trade_enabled": self.is_auto_trade_enabled,
            "mode": self.mode,
            "total_capital": round(self.total_capital, 2),
            "available_capital": round(self.available_capital, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "max_risk_amount": round(self.total_capital * (self.risk_per_trade_pct / 100.0), 2),
            "max_daily_loss": self.max_daily_loss,
            "min_consensus_required": self.min_consensus_required,
            "open_trades_count": len(self.open_trades),
            "closed_trades_count": len(self.closed_trades),
            "circuit_breaker_triggered": self.daily_pnl <= -self.max_daily_loss
        }

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculates conservative quantity strictly for the user's capital (e.g. ₹20,000).
        Risk Amount = Total Capital * Risk% (e.g. 20,000 * 1.5% = ₹300)
        Qty = Risk Amount / |Entry - SL|
        Ensures max intraday margin requirement does not exceed available capital with 5x leverage.
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 1

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance <= 0:
            sl_distance = entry_price * 0.005  # fallback 0.5%

        risk_amount = self.total_capital * (self.risk_per_trade_pct / 100.0)
        qty = int(risk_amount / sl_distance)

        # Max capital check: Intraday MIS gives 5x leverage (e.g. 20,000 capital -> ₹1,00,000 exposure)
        max_allowed_exposure = self.available_capital * 4.5  # conservative 4.5x
        max_qty_by_capital = int(max_allowed_exposure / entry_price)

        qty = min(qty, max_qty_by_capital)
        return max(1, qty)

    def evaluate_and_execute(self, setup: Dict[str, Any], upstox_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates a high-confidence signal and executes trade if eligible.
        """
        if not self.is_auto_trade_enabled:
            return None

        # Check circuit breaker
        if self.daily_pnl <= -self.max_daily_loss:
            logger.warning(f"[AUTO-TRADER] Circuit breaker triggered! Daily loss {self.daily_pnl} exceeded max loss limit -{self.max_daily_loss}.")
            return None

        # Consensus check
        consensus = setup.get("consensus_pct", 0)
        if consensus < self.min_consensus_required:
            return None

        # Must have clear BUY or SELL action
        action = setup.get("action", "")
        if "BUY" not in action and "SELL" not in action:
            return None

        symbol = setup.get("symbol", "")
        # Check if trade already open for this symbol
        for t in self.open_trades:
            if t["symbol"] == symbol and t["status"] == "OPEN":
                return None  # Already in an active trade for this symbol

        entry = float(setup.get("entry", 0.0))
        sl = float(setup.get("stop_loss", 0.0))
        tp = float(setup.get("target1", 0.0) or setup.get("target", 0.0))

        if entry <= 0 or sl <= 0:
            return None

        direction = "BUY" if "BUY" in action else "SELL"
        qty = self.calculate_position_size(entry, sl)
        est_margin = round((qty * entry) / 5.0, 2)  # MIS 5x margin needed

        if est_margin > self.available_capital:
            logger.info(f"[AUTO-TRADER] Insufficient margin for {symbol}. Required: ₹{est_margin}, Available: ₹{self.available_capital}")
            return None

        trade_id = f"TRD-{datetime.now().strftime('%y%m%d')}-{self.trade_counter:04d}"
        self.trade_counter += 1

        order_record = {
            "trade_id": trade_id,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "symbol": symbol,
            "direction": direction,
            "action": action,
            "quantity": qty,
            "entry_price": entry,
            "stop_loss": sl,
            "target": tp,
            "risk_reward": setup.get("risk_reward", "1:2.0"),
            "strategy": setup.get("strategy_title", "Institutional 15-Agent Consensus"),
            "status": "OPEN",
            "mode": self.mode,
            "margin_used": est_margin,
            "current_ltp": entry,
            "unrealized_pnl": 0.0,
            "pnl_pct": 0.0,
            "broker_order_id": None
        }

        # LIVE EXECUTION ON UPSTOX API
        if self.mode == "LIVE":
            broker_res = self._place_upstox_order(symbol, direction, qty, entry, upstox_config)
            if broker_res.get("success"):
                order_record["broker_order_id"] = broker_res.get("order_id", "LIVE_PLACED")
                order_record["broker_status"] = "SUCCESS"
            else:
                order_record["broker_status"] = f"FAILED: {broker_res.get('error')}"
                order_record["status"] = "FAILED"
                logger.error(f"[AUTO-TRADER] Upstox Live Order Failed: {broker_res.get('error')}")
                return order_record
        else:
            order_record["broker_order_id"] = f"PAPER-{trade_id}"
            order_record["broker_status"] = "SIMULATED_FILL"

        self.available_capital -= est_margin
        self.open_trades.append(order_record)
        logger.info(f"[AUTO-TRADER] {self.mode} order executed: {trade_id} | {direction} {qty} {symbol} @ ₹{entry} | SL: ₹{sl} | TP: ₹{tp}")
        return order_record

    def _place_upstox_order(self, symbol: str, direction: str, qty: int, entry: float, upstox_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends order request to Upstox API v2 endpoint: https://api.upstox.com/v2/order/place
        """
        access_token = upstox_config.get("access_token", "").strip()
        if not access_token:
            return {"success": False, "error": "Upstox Access Token is missing. Please save token in settings."}

        clean_symbol = symbol.replace(".NS", "").upper()
        instrument_token = UPSTOX_NSE_EQUITY_TOKENS.get(clean_symbol) or UPSTOX_NSE_EQUITY_TOKENS.get(symbol)
        
        if not instrument_token:
            # If not in hardcoded dictionary, default to NSE_EQ format
            instrument_token = f"NSE_EQ|{clean_symbol}"

        url = "https://api.upstox.com/v2/order/place"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        payload = {
            "quantity": int(qty),
            "product": "I",               # Intraday MIS
            "validity": "DAY",
            "price": 0.0,                 # 0.0 for MARKET order
            "tag": "AUTO_15_AI",
            "instrument_token": instrument_token,
            "order_type": "MARKET",
            "transaction_type": direction.upper(), # 'BUY' or 'SELL'
            "disclosed_quantity": 0,
            "trigger_price": 0.0,
            "is_amo": False
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            data = resp.json()
            if resp.status_code in [200, 201] and data.get("status") == "success":
                order_id = data.get("data", {}).get("order_id", "UPSTOX_SUCCESS")
                return {"success": True, "order_id": order_id}
            else:
                err_msg = data.get("errors", [{}])[0].get("message") if data.get("errors") else data.get("message", "Upstox rejected order")
                return {"success": False, "error": str(err_msg)}
        except Exception as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}

    def update_open_trades_with_ltp(self, symbol: str, current_ltp: float, upstox_config: Optional[Dict[str, Any]] = None):
        """
        Continuously checks open trades against live LTP to monitor Stop-Loss and Target hits.
        """
        for t in list(self.open_trades):
            if t["symbol"] != symbol or t["status"] != "OPEN":
                continue

            entry = t["entry_price"]
            sl = t["stop_loss"]
            tp = t["target"]
            qty = t["quantity"]
            is_buy = t["direction"] == "BUY"

            t["current_ltp"] = current_ltp
            diff = (current_ltp - entry) if is_buy else (entry - current_ltp)
            unrealized = round(diff * qty, 2)
            t["unrealized_pnl"] = unrealized
            t["pnl_pct"] = round((diff / entry) * 100, 2)

            # Check Target Hit
            hit_target = (current_ltp >= tp) if is_buy else (current_ltp <= tp)
            hit_sl = (current_ltp <= sl) if is_buy else (current_ltp >= sl)

            if hit_target or hit_sl:
                outcome = "TARGET HIT" if hit_target else "SL HIT"
                exit_price = tp if hit_target else sl
                exit_diff = (exit_price - entry) if is_buy else (entry - exit_price)
                realized_pnl = round(exit_diff * qty, 2)

                t["status"] = outcome
                t["exit_price"] = exit_price
                t["realized_pnl"] = realized_pnl
                t["exit_time"] = datetime.now().strftime("%H:%M:%S")

                # Release margin and update P&L
                self.available_capital += t["margin_used"]
                self.total_capital += realized_pnl
                self.daily_pnl += realized_pnl

                self.open_trades.remove(t)
                self.closed_trades.insert(0, t)

                logger.info(f"[AUTO-TRADER] {outcome}! Trade: {t['trade_id']} | Symbol: {symbol} | P&L: ₹{realized_pnl}")

                # If LIVE, exit position on Upstox
                if self.mode == "LIVE" and upstox_config:
                    exit_dir = "SELL" if is_buy else "BUY"
                    self._place_upstox_order(symbol, exit_dir, qty, exit_price, upstox_config)

    def get_all_trades(self) -> Dict[str, Any]:
        """Returns open and closed trades for frontend display."""
        return {
            "status": self.get_status(),
            "open_trades": self.open_trades,
            "closed_trades": self.closed_trades[:50]
        }
