"""
BidShield agent — scores conversation contexts, makes bid decisions,
generates creative for winning placements.

Uses Claude for scoring + creative generation, Tavily for context enrichment.
"""
import os
import json
import subprocess

# Initialize Overmind tracing — wraps all LLM calls automatically
_overmind_key = os.getenv("OVERMIND_API_KEY")
if _overmind_key:
    from overmind import init as overmind_init
    overmind_init(overmind_api_key=_overmind_key, service_name="bidshield")

from src.models import (
    CampaignBrief, ConversationContext, ContextScore, AdCreative,
    BidStreamResult, CampaignAction, AgentState,
)
from src import tools, supervisor


def ask_claude(prompt: str, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 600) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr[:200]}")
    return result.stdout.strip()


def _extract_json(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


def _check_forbidden_topics(context: ConversationContext, brief: CampaignBrief) -> str | None:
    """Fast local check — no LLM call needed."""
    prompt_lower = context.user_prompt.lower()
    for topic in brief.forbidden_topics:
        if topic.lower() in prompt_lower:
            return topic
    return None


def score_context(context: ConversationContext, brief: CampaignBrief, market_context: str = "") -> ContextScore:
    """Score a conversation context for brand fit, safety, and intent."""

    # Fast reject on forbidden topics
    forbidden_hit = _check_forbidden_topics(context, brief)
    if forbidden_hit:
        return ContextScore(
            context_id=context.id,
            brand_relevance=0,
            safety_risk=100,
            intent_strength=0,
            overall_score=0,
            reasoning=f"Forbidden topic detected: '{forbidden_hit}'. Auto-skip.",
        )

    prompt = f"""You are a media buying AI scoring a conversation context for ad placement.

BRAND BRIEF:
- Brand: {brief.brand}
- Objective: {brief.objective}
- Target audience: {brief.target_audience}
- Forbidden topics: {', '.join(brief.forbidden_topics)}
- Tone: {brief.tone}

CONVERSATION CONTEXT (the user prompt in an LLM channel):
Channel: {context.channel}
Category: {context.topic_category}
User prompt: "{context.user_prompt}"

{f"MARKET CONTEXT (from Tavily research):{chr(10)}{market_context[:600]}" if market_context else ""}

Score this context for ad placement suitability. Return ONLY valid JSON:
{{
  "brand_relevance": 0-100,
  "safety_risk": 0-100,
  "intent_strength": 0-100,
  "overall_score": 0-100,
  "reasoning": "one sentence"
}}

Scoring guide:
- brand_relevance: How well does this conversation match the brand's target audience and objective?
- safety_risk: How risky is it to place an ad here? (competitor mentions=40-60, sensitive topics=80+, safe=0-20)
- intent_strength: How strong is the purchase/action intent? (browsing=20, comparing=50, ready to buy=80+)
- overall_score: Weighted composite — high relevance + low risk + high intent = high score"""

    text = ask_claude(prompt)
    data = _extract_json(text)
    return ContextScore(context_id=context.id, **data)


def decide_bid(score: ContextScore) -> str:
    """Three-tier decision gate."""
    if score.safety_risk > 70:
        return "skipped"
    if score.overall_score >= 80:
        return "auto_bid"
    if score.overall_score >= 40:
        return "escalated"
    return "skipped"


def calculate_bid_cpm(context: ConversationContext, score: ContextScore, brief: CampaignBrief) -> float:
    """Calculate the CPM bid based on score and floor price."""
    # Bid between floor and max, scaled by score
    score_factor = score.overall_score / 100
    bid = context.floor_cpm_gbp + (brief.max_cpm_gbp - context.floor_cpm_gbp) * score_factor
    return round(min(bid, brief.max_cpm_gbp), 2)


def generate_creative(context: ConversationContext, brief: CampaignBrief) -> AdCreative:
    """Generate a conversational ad creative fitted to the context."""
    prompt = f"""You are an expert ad copywriter for conversational AI placements (sponsored answers in ChatGPT/Claude-style channels via Thrad).

The user asked: "{context.user_prompt}"
Brand: {brief.brand}
Objective: {brief.objective}
Tone: {brief.tone}

Write a sponsored conversational answer that feels natural, is clearly labelled as sponsored, and addresses the user's query while promoting the brand. Return ONLY valid JSON:
{{
  "headline": "short attention-grabbing headline",
  "body": "2-3 sentence sponsored answer that helps the user",
  "cta": "clear call to action",
  "target_keywords": ["keyword1", "keyword2", "keyword3"],
  "estimated_relevance_score": 0.0-1.0
}}"""

    text = ask_claude(prompt)
    data = _extract_json(text)
    return AdCreative(**data)


def process_context(
    context: ConversationContext,
    brief: CampaignBrief,
    state: AgentState,
    market_context: str = "",
) -> BidStreamResult:
    """Process a single conversation context through the full pipeline."""

    # Step 1: Score
    score = score_context(context, brief, market_context)

    score_action = CampaignAction(
        campaign_id=brief.id,
        action_type="score",
        description=f"Scored '{context.user_prompt[:50]}...' — {score.overall_score}/100",
        value=score.model_dump(),
    )
    state.actions.append(score_action)

    # Step 2: Decide
    decision = decide_bid(score)

    if decision == "skipped":
        skip_action = CampaignAction(
            campaign_id=brief.id,
            action_type="skip",
            description=f"Skipped: {score.reasoning}",
            value={"context_id": context.id, "reason": score.reasoning},
        )
        state.actions.append(skip_action)
        return BidStreamResult(
            context=context, score=score, decision="skipped",
        )

    if decision == "escalated":
        esc_action = CampaignAction(
            campaign_id=brief.id,
            action_type="escalate",
            description=f"Escalated for human review — score {score.overall_score}/100",
            value={"context_id": context.id, "score": score.overall_score},
        )
        state.actions.append(esc_action)
        return BidStreamResult(
            context=context, score=score, decision="escalated",
        )

    # Step 3: Auto-bid path — calculate bid + supervision check
    bid_cpm = calculate_bid_cpm(context, score, brief)

    bid_action = CampaignAction(
        campaign_id=brief.id,
        action_type="bid",
        description=f"Auto-bid £{bid_cpm:.2f} CPM on '{context.user_prompt[:40]}...'",
        value={"cpm_gbp": bid_cpm, "context_id": context.id, "estimated_impressions": context.estimated_impressions},
    )

    allowed, events = supervisor.apply_supervision(
        bid_action, state, brief.max_cpm_gbp, brief.daily_budget_gbp
    )

    if not allowed:
        return BidStreamResult(
            context=context, score=score, decision="blocked",
            bid_cpm_gbp=bid_cpm, supervision_events=events,
        )

    # Step 4: Generate creative for winning bid
    creative = generate_creative(context, brief)

    creative_action = CampaignAction(
        campaign_id=brief.id,
        action_type="creative_gen",
        description=f"Creative: '{creative.headline}'",
        value=creative.model_dump(),
    )
    state.actions.append(creative_action)

    # Calculate spend
    spend = bid_cpm * context.estimated_impressions / 1000
    state.total_spend_gbp += spend
    state.budget_remaining_gbp = brief.daily_budget_gbp - state.total_spend_gbp

    return BidStreamResult(
        context=context, score=score, decision="auto_bid",
        bid_cpm_gbp=bid_cpm, creative=creative, spend_gbp=spend,
    )


def process_escalation(
    result: BidStreamResult,
    approved: bool,
    brief: CampaignBrief,
    state: AgentState,
) -> BidStreamResult:
    """Handle human decision on an escalated placement."""
    result.human_approved = approved

    if not approved:
        result.decision = "skipped"
        return result

    # Human approved — bid and generate creative
    bid_cpm = calculate_bid_cpm(result.context, result.score, brief)
    result.bid_cpm_gbp = bid_cpm
    result.decision = "auto_bid"

    bid_action = CampaignAction(
        campaign_id=brief.id,
        action_type="bid",
        description=f"Human-approved bid £{bid_cpm:.2f} CPM",
        value={"cpm_gbp": bid_cpm, "context_id": result.context.id, "human_approved": True, "estimated_impressions": result.context.estimated_impressions},
    )

    allowed, events = supervisor.apply_supervision(
        bid_action, state, brief.max_cpm_gbp, brief.daily_budget_gbp
    )
    result.supervision_events = events

    if not allowed:
        result.decision = "blocked"
        return result

    creative = generate_creative(result.context, brief)
    result.creative = creative

    spend = bid_cpm * result.context.estimated_impressions / 1000
    result.spend_gbp = spend
    state.total_spend_gbp += spend
    state.budget_remaining_gbp = brief.daily_budget_gbp - state.total_spend_gbp

    return result
