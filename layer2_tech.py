from typing import Dict, Any
from .base_agent import BaseAgent, AgentVerdict

class TrendStructureAgent(BaseAgent):
    """Agent 4: Evaluates Dow Theory, Multi-timeframe EMA 9/20/50/200 alignment, and Trend Structure."""
    def __init__(self):
        super().__init__(
            agent_id=4,
            name="Trend & Market Structure",
            role="Dow Theory & Multi-EMA Trend Specialist",
            layer="Layer 2: Technical & Price Action",
            description="Evaluates EMA 9/20/50/200 stack alignment, higher highs/lows, and primary trend."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "EVALUATING_TREND_STRUCTURE"
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        ema9 = ind.get("ema9", ltp)
        ema20 = ind.get("ema20", ltp)
        ema50 = ind.get("ema50", ltp)
        ema200 = ind.get("ema200", ltp)

        # Bullish EMA Stack: Price > EMA9 > EMA20 > EMA50 > EMA200
        if ltp > ema9 > ema20 > ema50:
            vote = "BULLISH"
            score = 0.85
            confidence = 0.88
            above_200 = "above 200 EMA" if ltp > ema200 else "testing 200 EMA"
            rationale = f"Clean Bullish Trend Structure. Perfect bullish EMA alignment (Price > EMA9 > EMA20 > EMA50) and {above_200}."
        elif ltp < ema9 < ema20 < ema50:
            vote = "BEARISH"
            score = -0.85
            confidence = 0.88
            below_200 = "below 200 EMA" if ltp < ema200 else "breaking below 200 EMA"
            rationale = f"Clean Bearish Trend Structure. Bearish EMA cascade (Price < EMA9 < EMA20 < EMA50) and {below_200}."
        elif ltp > ema20 and ema9 > ema20:
            vote = "BULLISH"
            score = 0.50
            confidence = 0.68
            rationale = "Short-term momentum is bullish (Price > EMA9 > EMA20), intermediate trend consolidating."
        elif ltp < ema20 and ema9 < ema20:
            vote = "BEARISH"
            score = -0.50
            confidence = 0.68
            rationale = "Short-term momentum is bearish (Price < EMA9 < EMA20), intermediate trend weak."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = "EMAs are entwined. Sideways market structure without directional dominance."

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
            key_metrics={"ema9": ema9, "ema20": ema20, "ema50": ema50, "ema200": ema200}
        )
        self.last_verdict = verdict
        return verdict


class BreakoutHunterAgent(BaseAgent):
    """Agent 5: Detects Range breakouts, Bollinger Band Squeeze expansions, and identifies Fakeouts."""
    def __init__(self):
        super().__init__(
            agent_id=5,
            name="Breakout & Pattern Hunter",
            role="Range & Chart Pattern Breakout Specialist",
            layer="Layer 2: Technical & Price Action",
            description="Identifies High/Low breakouts, volatility squeezes, and filters fakeouts."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "HUNTING_BREAKOUTS"
        ltp = stock_data.get("ltp", 0.0)
        high = stock_data.get("high", ltp)
        low = stock_data.get("low", ltp)
        ind = stock_data.get("indicators", {})
        bb_upper = ind.get("bb_upper", ltp)
        bb_lower = ind.get("bb_lower", ltp)
        surge = ind.get("volume_surge", 1.0)
        pivots = ind.get("pivots", {})
        r1 = pivots.get("r1", ltp)
        s1 = pivots.get("s1", ltp)

        # Breakout condition: LTP breaking above Bollinger Upper or R1 with volume surge
        if ltp >= bb_upper and ltp >= r1:
            if surge >= 1.4:
                vote = "BULLISH"
                score = 0.90
                confidence = 0.88
                rationale = f"Genuine High-Volume Breakout! LTP {ltp} breached Upper Bollinger ({bb_upper:.2f}) and Pivot R1 ({r1:.2f}) supported by {surge:.2f}x volume surge."
            else:
                vote = "NEUTRAL"
                score = 0.20
                confidence = 0.55
                rationale = f"Breakout above Upper Bollinger ({bb_upper:.2f}) lacks volume confirmation ({surge:.2f}x). Potential bull trap / fakeout risk."
        elif ltp <= bb_lower and ltp <= s1:
            if surge >= 1.4:
                vote = "BEARISH"
                score = -0.90
                confidence = 0.88
                rationale = f"High-Volume Breakdown! LTP {ltp} slipped below Lower Bollinger ({bb_lower:.2f}) and Pivot S1 ({s1:.2f}) with {surge:.2f}x distribution volume."
            else:
                vote = "NEUTRAL"
                score = -0.20
                confidence = 0.55
                rationale = f"Breakdown below Lower Bollinger ({bb_lower:.2f}) lacks volume confirmation. Potential bear trap."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = f"Price trading within standard Bollinger envelope ({bb_lower:.2f} - {bb_upper:.2f}). No breakout trigger."

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
            key_metrics={"bb_upper": bb_upper, "bb_lower": bb_lower, "r1": r1, "s1": s1}
        )
        self.last_verdict = verdict
        return verdict


class MomentumOscillatorAgent(BaseAgent):
    """Agent 6: Evaluates RSI (14) momentum, divergence, and MACD histogram acceleration."""
    def __init__(self):
        super().__init__(
            agent_id=6,
            name="Momentum & Oscillators",
            role="RSI & MACD Momentum Acceleration Specialist",
            layer="Layer 2: Technical & Price Action",
            description="Analyzes RSI sweet zones (40-60-80), MACD crossovers, and hidden divergences."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "ANALYZING_OSCILLATORS"
        ind = stock_data.get("indicators", {})
        rsi = ind.get("rsi", 50.0)
        macd = ind.get("macd", 0.0)
        macd_signal = ind.get("macd_signal", 0.0)
        macd_hist = ind.get("macd_hist", 0.0)
        prev_hist = ind.get("prev_macd_hist", 0.0)

        # Bullish Momentum zone: RSI between 55 and 75, MACD > Signal and Hist expanding
        if 55 <= rsi <= 78 and macd > macd_signal and macd_hist > prev_hist:
            vote = "BULLISH"
            score = 0.85
            confidence = 0.86
            rationale = f"Strong Bullish Momentum Zone. RSI at {rsi:.1f} in power zone, MACD crossed above signal with accelerating histogram (+{macd_hist:.2f})."
        elif 22 <= rsi <= 45 and macd < macd_signal and macd_hist < prev_hist:
            vote = "BEARISH"
            score = -0.85
            confidence = 0.86
            rationale = f"Strong Bearish Momentum Zone. RSI at {rsi:.1f} slipping toward oversold, MACD below signal with widening negative histogram ({macd_hist:.2f})."
        elif rsi > 80:
            vote = "NEUTRAL"
            score = 0.10
            confidence = 0.60
            rationale = f"Caution: RSI extreme overbought at {rsi:.1f}. High risk of intraday mean-reversion pullbacks."
        elif rsi < 20:
            vote = "NEUTRAL"
            score = -0.10
            confidence = 0.60
            rationale = f"Caution: RSI extreme oversold at {rsi:.1f}. Risk of sharp short-covering bounces."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = f"RSI at {rsi:.1f} with flat MACD histogram. Momentum is dormant."

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
            key_metrics={"rsi": rsi, "macd": macd, "macd_hist": macd_hist}
        )
        self.last_verdict = verdict
        return verdict


class SupplyDemandZonesAgent(BaseAgent):
    """Agent 7: Identifies Institutional Supply/Demand Order Blocks, VWAP Reversion, and Pivot Levels."""
    def __init__(self):
        super().__init__(
            agent_id=7,
            name="Supply/Demand & VWAP",
            role="Order Blocks & Institutional Value Zone Specialist",
            layer="Layer 2: Technical & Price Action",
            description="Evaluates intraday VWAP support/resistance, classical pivots, and institutional zones."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "MAPPING_VALUE_ZONES"
        ltp = stock_data.get("ltp", 0.0)
        ind = stock_data.get("indicators", {})
        vwap = ind.get("vwap", ltp)
        pivots = ind.get("pivots", {})
        pivot = pivots.get("pivot", ltp)
        r1 = pivots.get("r1", ltp)
        s1 = pivots.get("s1", ltp)

        # VWAP interaction
        vwap_diff_pct = ((ltp - vwap) / vwap) * 100 if vwap else 0.0

        if ltp > vwap and 0.05 <= vwap_diff_pct <= 1.2 and ltp > pivot:
            vote = "BULLISH"
            score = 0.75
            confidence = 0.82
            rationale = f"Institutional Buyers in Control. LTP ({ltp}) holding firmly above Intraday VWAP ({vwap:.2f}) and above central Pivot ({pivot:.2f})."
        elif ltp < vwap and -1.2 <= vwap_diff_pct <= -0.05 and ltp < pivot:
            vote = "BEARISH"
            score = -0.75
            confidence = 0.82
            rationale = f"Sellers Dominating Value. LTP ({ltp}) rejected from VWAP ({vwap:.2f}) and trading below central Pivot ({pivot:.2f})."
        elif vwap_diff_pct > 2.5:
            vote = "NEUTRAL"
            score = 0.20
            confidence = 0.65
            rationale = f"Over-extended above VWAP (+{vwap_diff_pct:.2f}%). Re-test of VWAP zone expected before fresh longs."
        elif vwap_diff_pct < -2.5:
            vote = "NEUTRAL"
            score = -0.20
            confidence = 0.65
            rationale = f"Over-extended below VWAP ({vwap_diff_pct:.2f}%). Mean reversion bounce possible."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = f"LTP hugging VWAP ({vwap:.2f}). Fair value equilibrium with no directional edge."

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
            key_metrics={"vwap": vwap, "vwap_diff_pct": round(vwap_diff_pct, 2), "pivot": pivot}
        )
        self.last_verdict = verdict
        return verdict
