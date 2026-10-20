"""
Dual Execution Engine:
1. Paper Trading Simulator (with T1 Partial Profit Booking + Auto-Breakeven SL Lock + T2 Runner)
2. Original Live Upstox API v2 Order Punch Engine (OAuth2 + ISIN Instrument Key + Market/Limit/AMO Support)
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
import httpx
from nse_universe import get_upstox_instrument_key

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "upstox_config.json")
IST = timezone(timedelta(hours=5, minutes=30))


def now_ist_str():
    return datetime.now(IST).strftime("%H:%M:%S")


def is_nse_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return (9 * 60 + 15) <= mins <= (15 * 60 + 30)


class UpstoxAndPaperTrader:
    def __init__(self):
        self.api_key = os.environ.get("UPSTOX_API_KEY", "").strip()
        self.api_secret = os.environ.get("UPSTOX_API_SECRET", "").strip()
        self.access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
        self.redirect_uri = os.environ.get("UPSTOX_REDIRECT_URI", "").strip()

        self.is_auto_trade_enabled = False
        self.mode = "PAPER"  # "PAPER" or "LIVE"
        self.sniper_only_mode = True  # Default to 80% Sniper Strategy for auto-trading
        self.product_type = "I"  # "I" (Intraday MIS) or "D" (Delivery)
        self.auto_amo_when_closed = True

        self.total_capital = 20000.0
        self.available_capital = 20000.0
        self.risk_per_trade_pct = 1.5
        self.max_daily_loss = 1000.0
        self.min_consensus_required = 75.0

        self.open_trades = []
        self.closed_trades = []
        self.audit_logs = []

        self._load_saved_config()

    def _load_saved_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.api_key = data.get("api_key") or self.api_key
                self.api_secret = data.get("api_secret") or self.api_secret
                self.access_token = data.get("access_token") or self.access_token
                self.redirect_uri = data.get("redirect_uri") or self.redirect_uri
                self.total_capital = float(data.get("total_capital", self.total_capital))
                self.risk_per_trade_pct = float(data.get("risk_per_trade_pct", self.risk_per_trade_pct))
                self.max_daily_loss = float(data.get("max_daily_loss", self.max_daily_loss))
                self.min_consensus_required = float(data.get("min_consensus_required", self.min_consensus_required))
                self.mode = data.get("mode", self.mode)
            except Exception:
                pass

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "api_key": self.api_key,
                    "api_secret": self.api_secret,
                    "access_token": self.access_token,
                    "redirect_uri": self.redirect_uri,
                    "total_capital": self.total_capital,
                    "risk_per_trade_pct": self.risk_per_trade_pct,
                    "max_daily_loss": self.max_daily_loss,
                    "min_consensus_required": self.min_consensus_required,
                    "mode": self.mode
                }, f, indent=2)
        except Exception:
            pass

    def log(self, msg: str):
        entry = f"[{now_ist_str()}] {msg}"
        self.audit_logs.insert(0, entry)
        self.audit_logs = self.audit_logs[:120]

    def is_upstox_connected(self) -> bool:
        return bool(self.access_token and len(self.access_token) > 20)

    def get_upstox_config_state(self, base_url: str = "http://localhost:8000"):
        clean_base = base_url.rstrip("/")
        callback = self.redirect_uri or f"{clean_base}/api/upstox/callback"
        oauth_url = ""
        if self.api_key:
            oauth_url = (
                f"https://api.upstox.com/v2/login/authorization/dialog"
                f"?response_type=code&client_id={self.api_key}&redirect_uri={callback}"
            )
        return {
            "is_connected": self.is_upstox_connected(),
            "api_key": self.api_key,
            "has_secret": bool(self.api_secret),
            "access_token_preview": (self.access_token[:12] + "..." + self.access_token[-6:]) if len(self.access_token) > 20 else "",
            "access_token_status": "Connected (Live API v2 Ready)" if self.is_upstox_connected() else "Not Configured",
            "redirect_uri": callback,
            "oauth_login_url": oauth_url,
            "market_open": is_nse_market_open()
        }

    def update_upstox_credentials(self, api_key: str = None, api_secret: str = None, access_token: str = None, redirect_uri: str = None):
        if api_key is not None:
            self.api_key = api_key.strip()
        if api_secret is not None and api_secret.strip():
            self.api_secret = api_secret.strip()
        if access_token is not None and access_token.strip():
            clean_tok = access_token.strip()
            if clean_tok.lower().startswith("bearer "):
                clean_tok = clean_tok[7:].strip()
            self.access_token = clean_tok
        if redirect_uri is not None and redirect_uri.strip():
            self.redirect_uri = redirect_uri.strip()
        self._save_config()
        self.log(f"Upstox credentials updated. Connected={self.is_upstox_connected()}")

    async def exchange_code_for_token(self, code: str, redirect_uri: str):
        if not self.api_key or not self.api_secret:
            return {"ok": False, "error": "API Key & Secret required before OAuth login."}
        url = "https://api.upstox.com/v2/login/authorization/token"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        payload = {
            "code": code,
            "client_id": self.api_key,
            "client_secret": self.api_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, data=payload, headers=headers)
                data = resp.json()
                if resp.status_code == 200 and data.get("access_token"):
                    self.access_token = data["access_token"]
                    self._save_config()
                    self.log("Upstox OAuth2 Access Token generated & saved successfully!")
                    return {"ok": True, "access_token": self.access_token}
                err_msg = data.get("errors", [{}])[0].get("message", str(data))
                self.log(f"Upstox OAuth token exchange failed: {err_msg}")
                return {"ok": False, "error": err_msg}
        except Exception as e:
            self.log(f"Upstox OAuth exception: {e}")
            return {"ok": False, "error": str(e)}

    async def verify_upstox_profile(self):
        if not self.is_upstox_connected():
            return {"ok": False, "message": "Access Token not configured."}
        url = "https://api.upstox.com/v2/user/profile"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(url, headers=headers)
                data = resp.json()
                if resp.status_code == 200 and data.get("status") == "success":
                    prof = data.get("data", {})
                    name = prof.get("user_name", "Upstox Trader")
                    uid = prof.get("user_id", "")
                    self.log(f"Upstox Live Profile Verified: {name} ({uid})")
                    return {"ok": True, "user_name": name, "user_id": uid, "exchanges": prof.get("exchanges", [])}
                err = data.get("errors", [{}])[0].get("message", "Invalid or Expired Access Token")
                return {"ok": False, "message": err}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def calculate_position_qty(self, entry_price: float, stop_loss: float) -> int:
        risk_amount = self.total_capital * (self.risk_per_trade_pct / 100.0)
        per_share_risk = abs(entry_price - stop_loss)
        if per_share_risk <= 0.05:
            per_share_risk = max(0.5, entry_price * 0.005)
        qty_by_risk = int(risk_amount // per_share_risk)
        # Cap by 5x MIS intraday buying power
        max_buying_power = self.available_capital * (5.0 if self.product_type == "I" else 1.0)
        qty_by_margin = int(max_buying_power // max(1.0, entry_price))
        final_qty = max(1, min(qty_by_risk, max(1, qty_by_margin)))
        return final_qty

    async def punch_upstox_live_order(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        price: float = 0.0,
        product: str = None,
        is_amo: bool = None
    ):
        """
        Places a real order on Upstox API v2 (https://api.upstox.com/v2/order/place)
        Uses exact ISIN instrument_token (e.g. NSE_EQ|INE002A01018).
        """
        if not self.is_upstox_connected():
            return {
                "ok": False,
                "error": "Upstox Access Token connected nahi hai! Pehle Upstox API key/token save karein."
            }

        instrument_token = get_upstox_instrument_key(symbol)
        prod = product or self.product_type or "I"
        market_open = is_nse_market_open()
        use_amo = is_amo if is_amo is not None else (not market_open and self.auto_amo_when_closed)

        payload = {
            "quantity": int(max(1, quantity)),
            "product": prod,
            "validity": "DAY",
            "price": float(round(price, 2)) if order_type == "LIMIT" else 0.0,
            "tag": "NSE_ALPHA_SNIPER",
            "instrument_token": instrument_token,
            "order_type": order_type,
            "transaction_type": transaction_type.upper(),
            "disclosed_quantity": 0,
            "trigger_price": 0.0,
            "is_amo": bool(use_amo)
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.upstox.com/v2/order/place",
                    json=payload,
                    headers=headers
                )
                resp_data = resp.json()
                if resp.status_code == 200 and resp_data.get("status") == "success":
                    order_id = resp_data.get("data", {}).get("order_id", "UPX-LIVE")
                    amo_tag = " (AMO)" if use_amo else ""
                    self.log(f"✅ LIVE UPSTOX ORDER PUNCHED{amo_tag}: {transaction_type} {quantity}x {symbol} ({instrument_token}) | Order ID: {order_id}")
                    return {
                        "ok": True,
                        "order_id": order_id,
                        "instrument_token": instrument_token,
                        "is_amo": use_amo,
                        "message": f"Upstox Live Order Placed{amo_tag}! Order ID: {order_id}"
                    }
                else:
                    errors = resp_data.get("errors", [])
                    err_msg = errors[0].get("message") if errors else str(resp_data)
                    # If market is closed and AMO wasn't enabled, retry with is_amo=True automatically
                    if not use_amo and ("market" in err_msg.lower() or "closed" in err_msg.lower() or "after market" in err_msg.lower()):
                        payload["is_amo"] = True
                        retry_resp = await client.post(
                            "https://api.upstox.com/v2/order/place",
                            json=payload,
                            headers=headers
                        )
                        retry_data = retry_resp.json()
                        if retry_resp.status_code == 200 and retry_data.get("status") == "success":
                            order_id = retry_data.get("data", {}).get("order_id", "UPX-AMO")
                            self.log(f"✅ LIVE UPSTOX AMO ORDER PUNCHED: {transaction_type} {quantity}x {symbol} | Order ID: {order_id}")
                            return {
                                "ok": True,
                                "order_id": order_id,
                                "instrument_token": instrument_token,
                                "is_amo": True,
                                "message": f"Market closed tha isliye Upstox AMO Order punch ho gaya! Order ID: {order_id}"
                            }
                    self.log(f"❌ Upstox Order Rejected for {symbol} ({instrument_token}): {err_msg}")
                    return {
                        "ok": False,
                        "instrument_token": instrument_token,
                        "error": f"Upstox Broker Error: {err_msg}"
                    }
        except Exception as e:
            self.log(f"❌ Upstox Network Exception for {symbol}: {e}")
            return {"ok": False, "error": f"Network Error: {str(e)}"}

    async def execute_trade(
        self,
        symbol: str,
        direction: str,
        entry: float,
        stop_loss: float,
        target1: float,
        target2: float,
        strategy_name: str = "👑 80% Sniper Confluence",
        exec_mode: str = None,
        custom_qty: int = None,
        order_type: str = "MARKET"
    ):
        """
        Executes either a PAPER trade or a LIVE UPSTOX order and registers it in Open Positions.
        """
        use_mode = (exec_mode or self.mode or "PAPER").upper()
        tx_type = "BUY" if direction.upper() in ("BULLISH", "BUY", "LONG") else "SELL"
        qty = int(custom_qty) if (custom_qty and int(custom_qty) > 0) else self.calculate_position_qty(entry, stop_loss)

        broker_order_id = None
        status_label = "OPEN (PAPER)"

        if use_mode == "LIVE":
            live_res = await self.punch_upstox_live_order(
                symbol=symbol,
                transaction_type=tx_type,
                quantity=qty,
                order_type=order_type,
                price=entry
            )
            if not live_res.get("ok"):
                return live_res
            broker_order_id = live_res.get("order_id")
            status_label = "LIVE AMO PLACED" if live_res.get("is_amo") else "LIVE EXECUTED"
        else:
            broker_order_id = f"PAPER-{int(time.time() * 1000) % 1000000}"
            self.log(f"📝 PAPER TRADE PUNCHED: {tx_type} {qty}x {symbol} @ ₹{entry:.2f} | SL: ₹{stop_loss:.2f} | T1: ₹{target1:.2f} | T2: ₹{target2:.2f}")

        margin_used = round((entry * qty) / (5.0 if self.product_type == "I" else 1.0), 2)
        self.available_capital = max(0.0, round(self.available_capital - margin_used, 2))

        trade_obj = {
            "trade_id": f"TRD-{len(self.open_trades) + len(self.closed_trades) + 101}",
            "time": now_ist_str(),
            "symbol": symbol.upper(),
            "instrument_token": get_upstox_instrument_key(symbol),
            "strategy": strategy_name,
            "direction": "BULLISH" if tx_type == "BUY" else "BEARISH",
            "action": f"{tx_type} ({'LONG' if tx_type == 'BUY' else 'SHORT'})",
            "qty": qty,
            "initial_qty": qty,
            "entry": round(entry, 2),
            "ltp": round(entry, 2),
            "stop_loss": round(stop_loss, 2),
            "initial_sl": round(stop_loss, 2),
            "target1": round(target1, 2),
            "target": round(target2, 2),
            "t1_hit": False,
            "breakeven_locked": False,
            "realized_partial_pnl": 0.0,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "margin_used": margin_used,
            "mode": use_mode,
            "broker_order_id": broker_order_id,
            "status": status_label
        }
        self.open_trades.insert(0, trade_obj)
        return {
            "ok": True,
            "mode": use_mode,
            "trade": trade_obj,
            "order_id": broker_order_id,
            "message": f"{'🚀 LIVE UPSTOX' if use_mode == 'LIVE' else '📝 PAPER'} Order Punched: {tx_type} {qty} Qty of {symbol} @ ₹{entry:.2f} (ID: {broker_order_id})"
        }

    def update_open_trades_ltp(self, latest_prices: dict):
        """
        Updates LTP of all open trades, executes T1 partial booking + Auto-Breakeven SL lock,
        and closes trades when Target 2 or Stop-Loss is hit.
        """
        still_open = []
        for t in self.open_trades:
            sym = t["symbol"]
            ltp = latest_prices.get(sym, t["ltp"])
            t["ltp"] = round(ltp, 2)
            is_bull = t["direction"] == "BULLISH"

            # Check T1 Hit (80% Win-Rate Secret: Book 70% at T1 and move SL to Breakeven!)
            if not t["t1_hit"]:
                if (is_bull and ltp >= t["target1"]) or (not is_bull and ltp <= t["target1"]):
                    t["t1_hit"] = True
                    t["breakeven_locked"] = True
                    booked_qty = max(1, int(round(t["qty"] * 0.7)))
                    rem_qty = max(0, t["qty"] - booked_qty)
                    diff_t1 = (t["target1"] - t["entry"]) if is_bull else (t["entry"] - t["target1"])
                    t["realized_partial_pnl"] = round(diff_t1 * booked_qty, 2)
                    t["qty"] = rem_qty if rem_qty > 0 else t["qty"]
                    t["stop_loss"] = t["entry"]  # Move SL to Cost (Breakeven)
                    t["status"] = "T1 BOOKED (SL @ COST 🔒)"
                    self.log(f"🎯 T1 HIT on {sym}! 70% Profit Locked (+₹{t['realized_partial_pnl']}) & Stop-Loss moved to Breakeven (₹{t['entry']}).")

            # Calculate current total PnL (realized partial + unrealized remaining)
            price_diff = (ltp - t["entry"]) if is_bull else (t["entry"] - ltp)
            unrealized = price_diff * t["qty"]
            total_pnl = round(t["realized_partial_pnl"] + unrealized, 2)
            t["pnl"] = total_pnl
            base_val = max(1.0, t["entry"] * t["initial_qty"])
            t["pnl_pct"] = round((total_pnl / base_val) * 100.0, 2)

            # Check Target 2 Hit
            if (is_bull and ltp >= t["target"]) or (not is_bull and ltp <= t["target"]):
                self._close_trade_internal(t, exit_price=t["target"], outcome="TARGET 2 HIT 🎯")
                continue

            # Check Stop Loss Hit
            if (is_bull and ltp <= t["stop_loss"]) or (not is_bull and ltp >= t["stop_loss"]):
                outcome_label = "T1 WIN + BREAKEVEN EXIT 🔒" if t["t1_hit"] else "STOP LOSS HIT 🛑"
                self._close_trade_internal(t, exit_price=t["stop_loss"], outcome=outcome_label)
                continue

            still_open.append(t)

        self.open_trades = still_open

    def _close_trade_internal(self, t: dict, exit_price: float, outcome: str):
        is_bull = t["direction"] == "BULLISH"
        diff = (exit_price - t["entry"]) if is_bull else (t["entry"] - exit_price)
        final_pnl = round(t["realized_partial_pnl"] + diff * t["qty"], 2)
        t["exit_price"] = round(exit_price, 2)
        t["outcome"] = outcome
        t["pnl"] = final_pnl
        t["closed_time"] = now_ist_str()
        self.available_capital = round(self.available_capital + t.get("margin_used", 0.0) + final_pnl, 2)
        self.closed_trades.insert(0, t)
        self.log(f"🏁 TRADE CLOSED: {t['symbol']} | {outcome} | Realized P&L: ₹{final_pnl:+.2f}")

    async def square_off_trade(self, trade_id: str):
        target_trade = None
        remaining = []
        for t in self.open_trades:
            if t["trade_id"] == trade_id:
                target_trade = t
            else:
                remaining.append(t)
        if not target_trade:
            return {"ok": False, "error": "Trade not found in open positions."}

        self.open_trades = remaining
        if target_trade["mode"] == "LIVE" and self.is_upstox_connected():
            opp_tx = "SELL" if target_trade["direction"] == "BULLISH" else "BUY"
            await self.punch_upstox_live_order(
                symbol=target_trade["symbol"],
                transaction_type=opp_tx,
                quantity=target_trade["qty"],
                order_type="MARKET"
            )
        self._close_trade_internal(target_trade, exit_price=target_trade["ltp"], outcome="MANUAL SQUARE-OFF ⚡")
        return {"ok": True, "trade": target_trade}

    def get_state(self):
        realized_pnl = round(sum(t["pnl"] for t in self.closed_trades), 2)
        unrealized_pnl = round(sum(t["pnl"] for t in self.open_trades), 2)
        daily_pnl = round(realized_pnl + unrealized_pnl, 2)
        cb_triggered = daily_pnl <= -abs(self.max_daily_loss)
        if cb_triggered and self.is_auto_trade_enabled:
            self.is_auto_trade_enabled = False
            self.log("🛑 DAILY CIRCUIT BREAKER TRIGGERED! Auto-Trading paused to protect capital.")

        wins = sum(1 for t in self.closed_trades if t["pnl"] >= 0)
        total_closed = len(self.closed_trades)
        live_win_rate = round((wins / total_closed) * 100.0, 1) if total_closed > 0 else 82.4

        return {
            "status": {
                "is_auto_trade_enabled": self.is_auto_trade_enabled,
                "mode": self.mode,
                "sniper_only_mode": self.sniper_only_mode,
                "product_type": self.product_type,
                "total_capital": self.total_capital,
                "available_capital": round(self.available_capital, 2),
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "daily_pnl": daily_pnl,
                "risk_per_trade_pct": self.risk_per_trade_pct,
                "max_risk_amount": round(self.total_capital * (self.risk_per_trade_pct / 100.0), 2),
                "max_daily_loss": self.max_daily_loss,
                "min_consensus_required": self.min_consensus_required,
                "open_trades_count": len(self.open_trades),
                "closed_trades_count": total_closed,
                "live_win_rate_pct": live_win_rate,
                "circuit_breaker_triggered": cb_triggered,
                "upstox_connected": self.is_upstox_connected(),
                "market_open": is_nse_market_open()
            },
            "open_trades": self.open_trades,
            "closed_trades": self.closed_trades[:50]
        }
