from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentVerdict

class MasterArbiterAgent(BaseAgent):
    """Agent 14: Master Decision Arbiter. Aggregates all agent verdicts and enforces consensus filter."""
    def __init__(self, min_consensus: float = 0.70):
        super().__init__(
            agent_id=14,
            name="Master Decision Arbiter",
            role="Consensus Filter & Final Decision Authority",
            layer="Layer 5: Master Decision & Notification",
            description="Aggregates all 13 prior agent votes, calculates institutional consensus %, and approves/rejects setups."
        )
        self.min_consensus = min_consensus

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        # Default placeholder evaluate if called standalone
        return AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote="NEUTRAL",
            confidence=0.5,
            score=0.0,
            rationale="Awaiting prior agent evaluation committee."
        )

    def arbitrate(self, stock_data: Dict[str, Any], prior_verdicts: List[AgentVerdict]) -> AgentVerdict:
        """
        Synthesizes all 13 prior verdicts and determines final trade conviction.
        """
        self.status = "AGGREGATING_COMMITTEE_VOTES"
        total_agents = len(prior_verdicts)
        if total_agents == 0:
            return self.evaluate(stock_data, {})

        bullish_count = sum(1 for v in prior_verdicts if v.vote == "BULLISH")
        bearish_count = sum(1 for v in prior_verdicts if v.vote == "BEARISH")
        neutral_count = sum(1 for v in prior_verdicts if v.vote == "NEUTRAL")

        total_score = sum(v.score for v in prior_verdicts)
        avg_score = total_score / total_agents

        bullish_consensus = bullish_count / total_agents
        bearish_consensus = bearish_count / total_agents

        if bullish_consensus >= self.min_consensus:
            vote = "BULLISH"
            consensus_pct = bullish_consensus
            score = avg_score
            confidence = min(0.98, bullish_consensus + 0.1)
            rationale = (f"SETUP APPROVED (HIGH CONVICTION BULLISH). Institutional consensus reached with "
                         f"{bullish_count}/{total_agents} agents ({bullish_consensus*100:.1f}%) voting Bullish.")
        elif bearish_consensus >= self.min_consensus:
            vote = "BEARISH"
            consensus_pct = bearish_consensus
            score = avg_score
            confidence = min(0.98, bearish_consensus + 0.1)
            rationale = (f"SETUP APPROVED (HIGH CONVICTION BEARISH). Institutional consensus reached with "
                         f"{bearish_count}/{total_agents} agents ({bearish_consensus*100:.1f}%) voting Bearish.")
        else:
            vote = "NEUTRAL"
            consensus_pct = max(bullish_consensus, bearish_consensus)
            score = avg_score
            confidence = 0.50
            rationale = (f"SETUP REJECTED (LOW CONSENSUS). Market signals mixed: {bullish_count} Bullish, "
                         f"{bearish_count} Bearish, {neutral_count} Neutral. Minimum {self.min_consensus*100:.0f}% consensus required.")

        self.status = "IDLE"
        verdict = AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote=vote,
            confidence=confidence,
            score=round(score, 2),
            rationale=rationale,
            key_metrics={
                "bullish_votes": bullish_count,
                "bearish_votes": bearish_count,
                "neutral_votes": neutral_count,
                "consensus_pct": round(consensus_pct * 100, 1),
                "is_approved": vote in ["BULLISH", "BEARISH"]
            }
        )
        self.last_verdict = verdict
        return verdict


class AlertDispatcherAgent(BaseAgent):
    """Agent 15: Formats institutional trade tickets, logs setups, and dispatches alerts."""
    def __init__(self):
        super().__init__(
            agent_id=15,
            name="Alert Dispatcher & Reporter",
            role="Trade Ticket Generator & Alert Broadcast Specialist",
            layer="Layer 5: Master Decision & Notification",
            description="Generates complete trade setup cards (Entry, SL, Targets, Instrument) and dispatches alerts."
        )

    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        return AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote="NEUTRAL",
            confidence=0.5,
            score=0.0,
            rationale="Ready to format approved trade tickets."
        )

    def format_trade_ticket(self, stock_data: Dict[str, Any], arbiter_verdict: AgentVerdict,
                            risk_verdict: AgentVerdict, fno_verdict: AgentVerdict,
                            all_verdicts: List[AgentVerdict]) -> Dict[str, Any]:
        """
        Produces clean, production-ready Trade Ticket.
        """
        self.status = "DISPATCHING_TRADE_TICKET"
        symbol = stock_data.get("symbol", "")
        ltp = stock_data.get("ltp", 0.0)
        risk_metrics = risk_verdict.key_metrics if risk_verdict else {}
        fno_metrics = fno_verdict.key_metrics if fno_verdict else {}
        arbiter_metrics = arbiter_verdict.key_metrics if arbiter_verdict else {}

        vote = arbiter_verdict.vote
        is_approved = arbiter_metrics.get("is_approved", False)

        # Action formatting
        if vote == "BULLISH":
            action = "BUY CALL (CE)" if "atm_strike" in stock_data.get("fno", {}) else "INTRADAY BUY"
            instrument = f"{symbol} {fno_metrics.get('recommended_call', '')}" if "CE" in action else f"{symbol} EQ"
        elif vote == "BEARISH":
            action = "BUY PUT (PE)" if "atm_strike" in stock_data.get("fno", {}) else "INTRADAY SHORT"
            instrument = f"{symbol} {fno_metrics.get('recommended_put', '')}" if "PE" in action else f"{symbol} EQ"
        else:
            action = "NO TRADE / WATCH"
            instrument = f"{symbol} (Neutral)"

        ticket = {
            "ticket_id": f"TKT-{symbol}-{stock_data.get('timestamp', '').replace(':', '')}",
            "symbol": symbol,
            "action": action,
            "instrument": instrument,
            "status": "APPROVED" if is_approved else "WATCHLIST_ONLY",
            "direction": vote,
            "ltp": ltp,
            "change_pct": stock_data.get("change_pct", 0.0),
            "entry": risk_metrics.get("entry", ltp),
            "stop_loss": risk_metrics.get("stop_loss", ltp),
            "target1": risk_metrics.get("target1", ltp),
            "target2": risk_metrics.get("target2", ltp),
            "risk_reward": risk_metrics.get("risk_reward", "1:1.67"),
            "consensus_pct": arbiter_metrics.get("consensus_pct", 50.0),
            "bullish_votes": arbiter_metrics.get("bullish_votes", 0),
            "bearish_votes": arbiter_metrics.get("bearish_votes", 0),
            "neutral_votes": arbiter_metrics.get("neutral_votes", 0),
            "master_thesis": arbiter_verdict.rationale,
            "agent_breakdown": [v.to_dict() for v in all_verdicts],
            "timestamp": stock_data.get("timestamp", "")
        }

        self.status = "IDLE"
        self.last_verdict = AgentVerdict(
            agent_id=self.agent_id,
            name=self.name,
            role=self.role,
            layer=self.layer,
            vote=vote,
            confidence=0.95,
            score=arbiter_verdict.score,
            rationale=f"Ticket {ticket['ticket_id']} successfully generated and broadcasted.",
            key_metrics={"ticket_id": ticket["ticket_id"]}
        )
        return ticket
