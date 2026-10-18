from typing import Dict, Any
from .base_agent import BaseAgent, AgentVerdict

class MarketBreadthAgent(BaseAgent):
    """Agent 1: Evaluates Nifty 50, Bank Nifty, and Advance-Decline Market Breadth."""
    def __init__(self):
        super().__init__(
            agent_id=1,
            name="Market Pulse & Breadth",
            role="Macro Index & Market Tailwind Analyst",
            layer="Layer 1: Market & Orderflow",
            description="Monitors Nifty 50, Bank Nifty direction and advance/decline market breadth."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "ANALYZING_MARKET_TAILWINDS"
        nifty = market_pulse.get("nifty50", {})
        breadth = market_pulse.get("market_breadth", {})

        nifty_pct = nifty.get("change_pct", 0.0)
        stock_pct = stock_data.get("change_pct", 0.0)
        ratio = breadth.get("ratio", 1.0)

        # Consensus logic
        if nifty_pct > 0.1 and ratio >= 1.2:
            if stock_pct > 0:
                vote = "BULLISH"
                score = min(1.0, 0.5 + (nifty_pct / 2.0))
                confidence = min(0.95, 0.65 + (ratio * 0.1))
                rationale = f"Broad market is strongly bullish. Nifty up {nifty_pct:.2f}%, Adv/Dec ratio {ratio:.2f}. Positive tailwinds for {stock_data['symbol']}."
            else:
                vote = "NEUTRAL"
                score = -0.1
                confidence = 0.55
                rationale = f"Market is bullish (+{nifty_pct:.2f}%), but {stock_data['symbol']} is lagging with {stock_pct:.2f}%."
        elif nifty_pct < -0.1 and ratio <= 0.8:
            if stock_pct < 0:
                vote = "BEARISH"
                score = max(-1.0, -0.5 + (nifty_pct / 2.0))
                confidence = min(0.95, 0.70 + ((1.0 - ratio) * 0.2))
                rationale = f"Market is under heavy selling pressure. Nifty down {nifty_pct:.2f}%, Adv/Dec ratio {ratio:.2f}. High probability short tailwinds."
            else:
                vote = "NEUTRAL"
                score = 0.1
                confidence = 0.50
                rationale = f"Market is weak ({nifty_pct:.2f}%), but {stock_data['symbol']} showing isolated strength."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = "Market breadth is balanced and choppy. No clear macro index bias."

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
            key_metrics={"nifty_pct": nifty_pct, "adv_dec_ratio": ratio}
        )
        self.last_verdict = verdict
        return verdict


class VolumeSurgeAgent(BaseAgent):
    """Agent 2: Detects abnormal volume spikes and institutional liquidity footprints."""
    def __init__(self):
        super().__init__(
            agent_id=2,
            name="Volume Surge & Liquidity",
            role="Institutional Order Flow & Volume Scanner",
            layer="Layer 1: Market & Orderflow",
            description="Scans for 2x-5x volume surges and institutional participation."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "SCANNING_VOLUME_SURGES"
        ind = stock_data.get("indicators", {})
        surge = ind.get("volume_surge", 1.0)
        stock_pct = stock_data.get("change_pct", 0.0)

        if surge >= 2.0:
            if stock_pct > 0:
                vote = "BULLISH"
                score = min(1.0, 0.6 + (surge * 0.1))
                confidence = min(0.95, 0.75 + (surge * 0.05))
                rationale = f"Massive institutional volume surge detected! Current volume is {surge:.2f}x 20-period average with price moving up +{stock_pct:.2f}%."
            else:
                vote = "BEARISH"
                score = max(-1.0, -0.6 - (surge * 0.1))
                confidence = min(0.95, 0.75 + (surge * 0.05))
                rationale = f"Heavy institutional selling surge detected! Volume is {surge:.2f}x 20-period average on down move {stock_pct:.2f}%."
        elif surge >= 1.3:
            if stock_pct > 0:
                vote = "BULLISH"
                score = 0.45
                confidence = 0.65
                rationale = f"Healthy buying volume expansion ({surge:.2f}x average volume)."
            else:
                vote = "BEARISH"
                score = -0.45
                confidence = 0.65
                rationale = f"Elevated distribution volume ({surge:.2f}x average volume)."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = f"Volume is normal ({surge:.2f}x average). No abnormal institutional accumulation or distribution."

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
            key_metrics={"volume_surge_ratio": surge}
        )
        self.last_verdict = verdict
        return verdict


class DerivativesOIAgent(BaseAgent):
    """Agent 3: Analyzes F&O Open Interest Buildup, PCR, and Option Chain Sentiment."""
    def __init__(self):
        super().__init__(
            agent_id=3,
            name="Derivatives & F&O Open Interest",
            role="F&O Buildup & Option Greeks Specialist",
            layer="Layer 1: Market & Orderflow",
            description="Analyzes Long/Short Buildup, Put-Call Ratio (PCR), and Strike Pain."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "ANALYZING_OPTIONS_OI"
        fno = stock_data.get("fno", {})
        buildup = fno.get("buildup", "NEUTRAL")
        pcr = fno.get("pcr", 1.0)
        atm = fno.get("atm_strike", 0)

        if buildup == "LONG_BUILDUP" and pcr >= 1.1:
            vote = "BULLISH"
            score = 0.80
            confidence = 0.85
            rationale = f"F&O Long Buildup confirmed with strong PCR at {pcr:.2f}. Option writers heavily defending puts below strike {atm}."
        elif buildup == "SHORT_COVERING":
            vote = "BULLISH"
            score = 0.60
            confidence = 0.75
            rationale = f"Short covering rally underway in F&O contracts. Bears unwinding call positions at {atm} CE."
        elif buildup == "SHORT_BUILDUP" and pcr <= 0.8:
            vote = "BEARISH"
            score = -0.80
            confidence = 0.85
            rationale = f"Aggressive Short Buildup detected in F&O data. PCR weak at {pcr:.2f}. Heavy call writing at strike {atm}."
        elif buildup == "LONG_UNWINDING":
            vote = "BEARISH"
            score = -0.60
            confidence = 0.70
            rationale = f"Long unwinding pressure visible in F&O contracts. Bulls closing profitable long positions."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = f"F&O Open Interest buildup is neutral. PCR at {pcr:.2f} near equilibrium."

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
            key_metrics={"fno_buildup": buildup, "pcr": pcr, "atm_strike": atm}
        )
        self.last_verdict = verdict
        return verdict
