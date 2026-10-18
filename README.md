# NSE 15-AI-Agent Institutional Trading Terminal 🚀

An institutional-grade multi-agent autonomous trading setup for **NSE Intraday & F&O (Futures & Options)**. 

---

## 🏛️ 15-Agent Architecture Breakdown

### Layer 1: Market & Orderflow
* **Agent 1 - Market Pulse & Breadth:** Evaluates Nifty 50, Bank Nifty, and Advance-Decline market breadth.
* **Agent 2 - Volume Surge & Liquidity:** Detects abnormal 2x-5x volume surges and institutional footprints.
* **Agent 3 - Derivatives & F&O Open Interest:** Analyzes Long/Short buildup, Put-Call Ratio (PCR), and strike pain.

### Layer 2: Technical & Price Action
* **Agent 4 - Trend & Market Structure:** Dow theory, EMA 9/20/50/200 stack alignment, and multi-timeframe trend.
* **Agent 5 - Breakout & Pattern Hunter:** Range breakouts, Bollinger Band squeeze expansions, and fakeout filtering.
* **Agent 6 - Momentum & Oscillators:** RSI power zones (55-75), MACD crossovers, and histogram acceleration.
* **Agent 7 - Supply/Demand & VWAP:** VWAP holding/rejections, Pivot points (R1/R2/S1/S2), and institutional value zones.

### Layer 3: Macro & Institutional Sentiment
* **Agent 8 - News & Corporate Catalyst:** Tracks price/volume shocks driven by earnings, corporate announcements, and block deals.
* **Agent 9 - Global Cues & India VIX:** India VIX volatility regime (Low, Elevated, High) and risk-reward environment.
* **Agent 10 - Institutional Smart Money Flow:** FII/DII broad flow direction and smart money delivery absorption.

### Layer 4: Strategy & Execution
* **Agent 11 - Intraday Momentum Scalper:** 5-minute candle triggers, 9 EMA rides, and immediate day trading momentum.
* **Agent 12 - F&O Options & Futures Strategist:** Selects specific ATM/OTM Call/Put strikes (CE/PE) and spreads.
* **Agent 13 - Risk Management & Sizing:** ATR-based exact Stop Loss, Target 1 (1:1.5+), Target 2 (1:2.5+), and R:R enforcement.

### Layer 5: Master Decision & Notification
* **Agent 14 - Master Decision Arbiter:** Aggregates all 13 prior agent votes. Enforces minimum 70% committee consensus before approving setups.
* **Agent 15 - Alert Dispatcher & Reporter:** Generates production-ready trade tickets and dispatches live web and audio notifications.

---

## 🚀 How to Run

1. **Direct Web Access:**
   If already running in background, open:
   👉 **`http://127.0.0.1:8000`** in your browser.

2. **One-Click Startup:**
   Double click `start.bat` in this folder:
   `C:\Users\sskum\.gemini\antigravity\scratch\nse-15-agent-trader\start.bat`

3. **Broker Integration:**
   Click the **Key icon** in the top navigation bar to connect your **Upstox API** token for direct broker feeds. If left blank, it automatically uses free open-source NSE & Yahoo Finance data.
