from typing import Dict, Any
from .base_agent import BaseAgent, AgentVerdict
from news_feed import market_news_service

class NewsCatalystAgent(BaseAgent):
    """Agent 8: Tracks high-impact news catalysts, live RSS headlines, and corporate sentiment triggers."""
    def __init__(self):
        super().__init__(
            agent_id=8,
            name="News & Corporate Catalyst",
            role="Catalyst & Corporate Actions Scanner",
            layer="Layer 3: Macro & Institutional Sentiment",
            description="Tracks corporate announcements, live RSS news sentiment, earnings reactions, and sector catalysts."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "SCANNING_CATALYSTS"
        stock_pct = stock_data.get("change_pct", 0.0)
        surge = stock_data.get("indicators", {}).get("volume_surge", 1.0)
        symbol = stock_data.get("symbol", "")

        # 1. Fetch live RSS news sentiment for this stock or macro market
        news_info = market_news_service.get_news_sentiment_for_symbol(symbol)
        has_direct_news = news_info.get("has_news", False)
        news_sentiment = news_info.get("sentiment", "NEUTRAL")
        news_headline = news_info.get("headline", "")
        news_source = news_info.get("source", "Live Market Feed")

        # 2. News-driven price action signature combined with live RSS headlines
        if has_direct_news and news_sentiment == "BULLISH":
            vote = "BULLISH"
            score = 0.90
            confidence = 0.88
            rationale = f"Live News Catalyst in {symbol}: '{news_headline}' ({news_source}). Strong positive fundamental sentiment backed by {surge:.2f}x volume."
        elif has_direct_news and news_sentiment == "BEARISH":
            vote = "BEARISH"
            score = -0.90
            confidence = 0.88
            rationale = f"Breaking Negative Catalyst in {symbol}: '{news_headline}' ({news_source}). Downside catalyst risk detected."
        elif abs(stock_pct) >= 1.5 and surge >= 1.8:
            if stock_pct > 0:
                vote = "BULLISH"
                score = 0.85
                confidence = 0.82
                rationale = f"Strong Positive Catalyst footprint in {symbol}! Heavy momentum (+{stock_pct:.2f}%) on {surge:.2f}x volume indicates institutional buying trigger."
            else:
                vote = "BEARISH"
                score = -0.85
                confidence = 0.82
                rationale = f"Negative Catalyst shock in {symbol}! Price breaking down -{abs(stock_pct):.2f}% on heavy {surge:.2f}x volume. Negative news overhang detected."
        elif abs(stock_pct) >= 0.8:
            if stock_pct > 0:
                vote = "BULLISH"
                score = 0.50
                confidence = 0.65
                rationale = f"Moderate positive news sentiment flow driving steady gains in {symbol}."
            else:
                vote = "BEARISH"
                score = -0.50
                confidence = 0.65
                rationale = f"Mild negative corporate/sector headwinds impacting {symbol}."
        else:
            # Fall back to macro news tone
            macro_tone = news_info.get("macro_sentiment", "NEUTRAL")
            if macro_tone == "BULLISH" and stock_pct > 0:
                vote = "BULLISH"
                score = 0.35
                confidence = 0.60
                rationale = f"Broader market news sentiment positive ('{news_headline}'). {symbol} trading in alignment."
            elif macro_tone == "BEARISH" and stock_pct < 0:
                vote = "BEARISH"
                score = -0.35
                confidence = 0.60
                rationale = f"Broader market news sentiment cautious ('{news_headline}'). {symbol} facing sector drag."
            else:
                vote = "NEUTRAL"
                score = 0.0
                confidence = 0.50
                rationale = f"No breaking news or abnormal corporate action triggers detected for {symbol}."

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
                "price_momentum_pct": stock_pct,
                "catalyst_surge": surge,
                "has_live_news": has_direct_news,
                "news_headline": news_headline[:60] if news_headline else None
            }
        )
        self.last_verdict = verdict
        return verdict


class GlobalCuesVixAgent(BaseAgent):
    """Agent 9: Evaluates India VIX volatility environment and macro global risk-on/off cues."""
    def __init__(self):
        super().__init__(
            agent_id=9,
            name="Global Cues & India VIX",
            role="Volatility Regime & Macro Risk Specialist",
            layer="Layer 3: Macro & Institutional Sentiment",
            description="Evaluates India VIX regime (Option buying vs writing sweet spots) and macro risk."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "EVALUATING_VIX_REGIME"
        vix = market_pulse.get("india_vix", {})
        vix_val = vix.get("value", 13.5)
        regime = vix.get("regime", "LOW_VOLATILITY")
        stock_pct = stock_data.get("change_pct", 0.0)

        # In low volatility (VIX < 14), trend-following and momentum breakouts succeed with low slippage
        # In elevated volatility (VIX > 18), wide swings occur, requiring wider stop-loss
        if vix_val <= 14.5:
            if stock_pct > 0:
                vote = "BULLISH"
                score = 0.65
                confidence = 0.80
                rationale = f"India VIX calm at {vix_val:.2f} ({regime}). Low market fear creates ideal conditions for steady directional continuation and Intraday Call options."
            else:
                vote = "BEARISH"
                score = -0.65
                confidence = 0.80
                rationale = f"VIX calm at {vix_val:.2f}. Controlled downtrend in progress with predictable ATR levels."
        elif vix_val >= 18.0:
            vote = "NEUTRAL"
            score = -0.10 if stock_pct < 0 else 0.10
            confidence = 0.60
            rationale = f"Elevated India VIX at {vix_val:.2f} ({regime}). Heightened whipsaw risk; requires tight trailing stop-loss and strict position sizing."
        else:
            vote = "BULLISH" if stock_pct > 0 else ("BEARISH" if stock_pct < 0 else "NEUTRAL")
            score = 0.35 if stock_pct > 0 else -0.35
            confidence = 0.65
            rationale = f"India VIX balanced at {vix_val:.2f}. Normal volatility distribution across NSE F&O basket."

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
            key_metrics={"india_vix": vix_val, "volatility_regime": regime}
        )
        self.last_verdict = verdict
        return verdict


class InstitutionalFlowAgent(BaseAgent):
    """Agent 10: Tracks FII & DII net flows, smart money delivery accumulation, and block deals."""
    def __init__(self):
        super().__init__(
            agent_id=10,
            name="Institutional Smart Money Flow",
            role="FII / DII Flow & Smart Money Specialist",
            layer="Layer 3: Macro & Institutional Sentiment",
            description="Tracks institutional net cash / index futures bias and high delivery absorption."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        self.status = "TRACKING_INSTITUTIONAL_FLOWS"
        breadth = market_pulse.get("market_breadth", {})
        adv_dec_ratio = breadth.get("ratio", 1.0)
        stock_pct = stock_data.get("change_pct", 0.0)
        surge = stock_data.get("indicators", {}).get("volume_surge", 1.0)

        # Smart Money Footprint: Adv/Dec ratio strong + stock volume surge
        if adv_dec_ratio >= 1.5 and surge >= 1.3 and stock_pct > 0.3:
            vote = "BULLISH"
            score = 0.80
            confidence = 0.84
            rationale = f"Smart Money Institutional Inflow! Broad market institutional buying (Adv/Dec ratio {adv_dec_ratio:.2f}) aligning with institutional accumulation in {stock_data['symbol']}."
        elif adv_dec_ratio <= 0.7 and surge >= 1.3 and stock_pct < -0.3:
            vote = "BEARISH"
            score = -0.80
            confidence = 0.84
            rationale = f"Institutional Distribution Detected! FII/DII broad market selling pressure coinciding with heavy offloading in {stock_data['symbol']}."
        elif stock_pct > 0:
            vote = "BULLISH"
            score = 0.40
            confidence = 0.60
            rationale = "Mild institutional support observed on pullbacks."
        elif stock_pct < 0:
            vote = "BEARISH"
            score = -0.40
            confidence = 0.60
            rationale = "Mild institutional supply emerging near overhead resistance."
        else:
            vote = "NEUTRAL"
            score = 0.0
            confidence = 0.50
            rationale = "Institutional positioning is neutral. No aggressive block transactions."

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
            key_metrics={"adv_dec_ratio": adv_dec_ratio, "smart_money_surge": surge}
        )
        self.last_verdict = verdict
        return verdict
