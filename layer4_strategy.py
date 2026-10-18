from typing import Dict, Any
from .base_agent import BaseAgent, AgentVerdict

class IntradayScalpAgent(BaseAgent):
    """Agent 11: Generates 5m timeframe Intraday momentum scalp triggers."""
    def __init__(self):
        super().__init__(
            agent_id=11,
            name="Intraday Momentum Scalper",
            role="5m Quick Trigger & Scalp Specialist",
            layer="Layer 4: Strategy & Execution",
            description="Evaluates 5-minute candle velocity, EMA 9 pullbacks, and immediate day trading triggers."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "CALCULATING_INTRADAY_TRIGGERS"
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        ema9 = ind.get("ema9", ltp)
        vwap = ind.get("vwap", ltp)
        rsi = ind.get("rsi", 50.0)

        # Scalp long: Price above EMA9 and VWAP, RSI between 52 and 72
        if ltp > ema9 and ltp > vwap and 52 <= rsi <= 74:
            vote = "BULLISH"
            score = 0.85
            confidence = 0.85
            rationale = f"High-Velocity Intraday Scalp Trigger! Price {ltp} riding above 9 EMA ({ema9:.2f}) and VWAP ({vwap:.2f}) with RSI {rsi:.1f} in prime acceleration zone."
        # Scalp short: Price below EMA9 and VWAP, RSI between 26 and 48
        elif ltp < ema9 and ltp < vwap and 26 <= rsi <= 48:
            vote = "BEARISH"
            score = -0.85
            confidence = 0.85
            rationale = f"High-Velocity Intraday Short Trigger! Price {ltp} breaking down below 9 EMA ({ema9:.2f}) and VWAP ({vwap:.2f}) with RSI {rsi:.1f} diving."
        elif ltp > ema9:
            vote = "BULLISH"
            score = 0.40
            confidence = 0.60
            rationale = "Mild intraday bullish bias above 9 EMA."
        elif ltp < ema9:
            vote = "BEARISH"
            score = -0.40
            confidence = 0.60
            rationale = "Mild intraday bearish pressure below 9 EMA."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = "No decisive 5m intraday momentum trigger present."

        self.status = "IDLE"
        verdict = AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote=vote,
            confidence=confidence,
            score=score,
            rationale=rationale,
            key_metrics={"intraday_ema9": ema9, "rsi_5m": rsi}
        )
        self.last_verdict = verdict
        return verdict


class FnoSwingAgent(BaseAgent):
    """Agent 12: Formulates F&O option strikes (Calls/Puts) and Futures positioning."""
    def __init__(self):
        super().__init__(
            agent_id=12,
            name="F&O Options & Futures Strategist",
            role="Derivative Strike & Contract Selection Specialist",
            layer="Layer 4: Strategy & Execution",
            description="Recommends specific Call/Put option strikes, expiry, and Futures bias."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "DESIGNING_FNO_CONTRACTS"
        ltp = stock_data.get("ltp", 0.0)
        fno = stock_data.get("fno", {})
        atm = fno.get("atm_strike", round(ltp))
        call_strike = fno.get("call_strike", atm + 50)
        put_strike = fno.get("put_strike", atm - 50)
        buildup = fno.get("buildup", "NEUTRAL")
        pcr = fno.get("pcr", 1.0)
        stock_pct = stock_data.get("change_pct", 0.0)

        if buildup in ["LONG_BUILDUP", "SHORT_COVERING"] and stock_pct > 0.2:
            vote = "BULLISH"
            score = 0.85
            confidence = 0.85
            rationale = f"Recommended F&O Trade: BUY {stock_data['symbol']} {atm} CE or Bull Call Spread. F&O momentum points to target {call_strike} CE with PCR {pcr:.2f}."
        elif buildup in ["SHORT_BUILDUP", "LONG_UNWINDING"] and stock_pct < -0.2:
            vote = "BEARISH"
            score = -0.85
            confidence = 0.85
            rationale = f"Recommended F&O Trade: BUY {stock_data['symbol']} {atm} PE or Bear Put Spread. F&O breakdown targeting {put_strike} PE with weak PCR {pcr:.2f}."
        elif stock_pct > 0:
            vote = "BULLISH"
            score = 0.35
            confidence = 0.60
            rationale = f"Mild bullish bias in F&O contracts near strike {atm}."
        elif stock_pct < 0:
            vote = "BEARISH"
            score = -0.35
            confidence = 0.60
            rationale = f"Mild bearish bias in F&O contracts near strike {atm}."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = "Option open interest balanced across both CE and PE strikes."

        self.status = "IDLE"
        verdict = AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote=vote,
            confidence=confidence,
            score=score,
            rationale=rationale,
            key_metrics={"recommended_call": f"{atm} CE", "recommended_put": f"{atm} PE", "pcr": pcr}
        )
        self.last_verdict = verdict
        return verdict


class RiskManagementAgent(BaseAgent):
    """Agent 13: Calculates precise Stop Loss, Target 1, Target 2, and enforces Minimum 1:1.5 Risk-Reward."""
    def __init__(self):
        super().__init__(
            agent_id=13,
            name="Risk Management & Sizing",
            role="Stop-Loss, Target & Risk-to-Reward Officer",
            layer="Layer 4: Strategy & Execution",
            description="Calculates exact ATR-based Stop Loss, Target 1 (1:1.5), Target 2 (1:2.5+), and protects capital."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "ENFORCING_RISK_REWARD"
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        atr = ind.get("atr", max(1.0, ltp * 0.008))
        stock_pct = stock_data.get("change_pct", 0.0)

        # Risk parameters: SL is 1.5x ATR, Target 1 is 2.5x ATR (1:1.67 R:R), Target 2 is 4.0x ATR (1:2.67 R:R)
        sl_distance = round(atr * 1.5, 2)
        tgt1_distance = round(atr * 2.5, 2)
        tgt2_distance = round(atr * 4.0, 2)
        rr_ratio = round(tgt1_distance / (sl_distance + 1e-9), 2)

        if stock_pct >= 0:
            vote = "BULLISH"
            score = 0.80
            confidence = 0.90
            entry = ltp
            sl = round(ltp - sl_distance, 2)
            tgt1 = round(ltp + tgt1_distance, 2)
            tgt2 = round(ltp + tgt2_distance, 2)
            rationale = (f"Risk Parameters Validated: Entry @ ₹{entry:.2f} | Stop Loss @ ₹{sl:.2f} (Risk: ₹{sl_distance:.2f}) | "
                         f"Target 1 @ ₹{tgt1:.2f} (Reward: ₹{tgt1_distance:.2f}) | Target 2 @ ₹{tgt2:.2f} | R:R Ratio = 1:{rr_ratio:.2f} (Approved).")
        else:
            vote = "BEARISH"
            score = -0.80
            confidence = 0.90
            entry = ltp
            sl = round(ltp + sl_distance, 2)
            tgt1 = round(ltp - tgt1_distance, 2)
            tgt2 = round(ltp - tgt2_distance, 2)
            rationale = (f"Risk Parameters Validated: Short Entry @ ₹{entry:.2f} | Stop Loss @ ₹{sl:.2f} (Risk: ₹{sl_distance:.2f}) | "
                         f"Target 1 @ ₹{tgt1:.2f} (Reward: ₹{tgt1_distance:.2f}) | Target 2 @ ₹{tgt2:.2f} | R:R Ratio = 1:{rr_ratio:.2f} (Approved).")

        self.status = "IDLE"
        verdict = AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote=vote,
            confidence=confidence,
            score=score,
            rationale=rationale,
            key_metrics={
                "entry": entry,
                "stop_loss": sl,
                "target1": tgt1,
                "target2": tgt2,
                "risk_reward": f"1:{rr_ratio:.2f}"
            }
        )
        self.last_verdict = verdict
        return verdict
