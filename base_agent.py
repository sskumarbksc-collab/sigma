from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

@dataclass
class AgentVerdict:
    agent_id: int
    name: str
    role: str
    layer: str
    vote: str            # 'BULLISH', 'BEARISH', 'NEUTRAL'
    confidence: float    # 0.0 to 1.0 (e.g. 0.85 = 85%)
    score: float         # -1.0 (strong sell) to +1.0 (strong buy)
    rationale: str       # Clear reasoning for the setup
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "layer": self.layer,
            "vote": self.vote,
            "confidence": round(self.confidence * 100, 1),
            "score": round(self.score, 2),
            "rationale": self.rationale,
            "key_metrics": self.key_metrics,
            "timestamp": self.timestamp
        }

class BaseAgent(ABC):
    """Abstract Base Class for all 15 Trading Agents"""
    def __init__(self, agent_id: int, name: str, role: str, layer: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.layer = layer
        self.description = description
        self.status = "IDLE"
        self.last_verdict: Optional[AgentVerdict] = None

    @abstractmethod
    def evaluate(self, stock_data: Dict[str, Any], market_pulse: Dict[str, Any]) -> AgentVerdict:
        """
        Analyze incoming stock indicators and market context, returning a verdict.
        """
        pass
