from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime
import uuid


class CampaignBrief(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    brand: str
    objective: str
    target_audience: str
    daily_budget_gbp: float
    max_cpm_gbp: float = 5.0
    forbidden_topics: list[str] = Field(default_factory=lambda: [
        "gambling", "adult content", "cryptocurrency scams", "weapons",
    ])
    tone: str = "professional, helpful, authoritative"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationContext(BaseModel):
    """An ad opportunity — a user prompt in an LLM channel."""
    id: str
    user_prompt: str
    channel: str
    topic_category: str
    estimated_impressions: int
    floor_cpm_gbp: float


class ContextScore(BaseModel):
    """Claude's evaluation of a conversation context against the brand brief."""
    context_id: str
    brand_relevance: float  # 0-100
    safety_risk: float      # 0-100 (high = dangerous)
    intent_strength: float  # 0-100 (high = strong purchase intent)
    overall_score: float    # weighted composite
    reasoning: str


class AdCreative(BaseModel):
    headline: str
    body: str
    cta: str
    target_keywords: list[str]
    estimated_relevance_score: float  # 0-1


class BidDecision(BaseModel):
    campaign_id: str
    context_snippet: str
    recommended_cpm_gbp: float
    rationale: str
    confidence: float  # 0-1


class CampaignAction(BaseModel):
    """A single action taken by the campaign agent — logged for supervision."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    campaign_id: str
    action_type: Literal["research", "creative_gen", "bid", "score", "skip", "escalate", "report"]
    description: str
    value: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SupervisionEvent(BaseModel):
    """Raised by the Overmind supervision layer when anomalies are detected."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: Literal["info", "warning", "critical"]
    rule_violated: str
    description: str
    action_id: str
    agent_paused: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BidStreamResult(BaseModel):
    """Outcome of one bid decision in the stream."""
    context: ConversationContext
    score: ContextScore | None = None
    decision: Literal["auto_bid", "escalated", "skipped", "blocked"]
    bid_cpm_gbp: float | None = None
    creative: AdCreative | None = None
    supervision_events: list[SupervisionEvent] = Field(default_factory=list)
    human_approved: bool | None = None  # None if not escalated
    spend_gbp: float = 0.0


class AgentState(BaseModel):
    status: Literal["running", "paused", "halted", "complete"] = "running"
    current_campaign_id: str | None = None
    actions: list[CampaignAction] = Field(default_factory=list)
    supervision_events: list[SupervisionEvent] = Field(default_factory=list)
    results: list[BidStreamResult] = Field(default_factory=list)
    total_spend_gbp: float = 0.0
    budget_remaining_gbp: float = 0.0
