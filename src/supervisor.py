"""
Overmind supervision layer.

Checks every agent action against guardrails before it's committed.
When the real Overmind SDK is available, replace mock with actual SDK calls.
"""
from src.models import CampaignAction, SupervisionEvent, AgentState


# ── Guardrail definitions ─────────────────────────────────────────────────────

GUARDRAILS = {
    "max_cpm_ceiling": {
        "description": "CPM cannot exceed 3x the campaign max_cpm_gbp",
        "severity": "critical",
    },
    "budget_spike": {
        "description": "Single bid cannot exceed 20% of daily budget",
        "severity": "critical",
    },
    "budget_exhaustion": {
        "description": "Total spend cannot exceed daily budget",
        "severity": "critical",
    },
    "content_safety": {
        "description": "Ad creative cannot contain prohibited categories",
        "severity": "warning",
    },
    "bid_drift": {
        "description": "Three consecutive bids above campaign ceiling trigger review",
        "severity": "warning",
    },
}

PROHIBITED_KEYWORDS = [
    "guaranteed returns", "risk-free", "casino", "crypto guaranteed",
    "weight loss miracle", "cure", "unlimited money",
]


# ── Supervision functions ─────────────────────────────────────────────────────

def check_action(
    action: CampaignAction,
    state: AgentState,
    campaign_max_cpm: float,
    daily_budget: float,
) -> list[SupervisionEvent]:
    """
    Evaluate a proposed action against guardrails.
    Returns a list of SupervisionEvents (empty = all clear).
    """
    events = []

    if action.action_type == "bid":
        cpm = action.value.get("cpm_gbp", 0)

        # Rule 1: CPM ceiling (3x max)
        if cpm > campaign_max_cpm * 3:
            events.append(SupervisionEvent(
                severity="critical",
                rule_violated="max_cpm_ceiling",
                description=f"CPM £{cpm:.2f} exceeds 3x campaign ceiling (£{campaign_max_cpm * 3:.2f}). Agent halted.",
                action_id=action.id,
                agent_paused=True,
            ))

        # Rule 2: Budget spike (single bid > 20% of daily)
        estimated_spend = cpm * 50  # rough estimate for 50k impressions
        if estimated_spend > daily_budget * 0.20:
            events.append(SupervisionEvent(
                severity="warning",
                rule_violated="budget_spike",
                description=f"Estimated spend £{estimated_spend:.2f} from this bid exceeds 20% of daily budget.",
                action_id=action.id,
                agent_paused=False,
            ))

        # Rule 3: Budget exhaustion
        if state.total_spend_gbp + estimated_spend > daily_budget:
            events.append(SupervisionEvent(
                severity="critical",
                rule_violated="budget_exhaustion",
                description=f"This bid would exceed daily budget (£{daily_budget:.2f}). Current spend: £{state.total_spend_gbp:.2f}. Agent halted.",
                action_id=action.id,
                agent_paused=True,
            ))

    if action.action_type == "creative_gen":
        creative_text = str(action.value).lower()
        for keyword in PROHIBITED_KEYWORDS:
            if keyword in creative_text:
                events.append(SupervisionEvent(
                    severity="warning",
                    rule_violated="content_safety",
                    description=f"Creative contains prohibited keyword: '{keyword}'",
                    action_id=action.id,
                    agent_paused=False,
                ))

    return events


def apply_supervision(
    action: CampaignAction,
    state: AgentState,
    campaign_max_cpm: float,
    daily_budget: float,
) -> tuple[bool, list[SupervisionEvent]]:
    """
    Check action, record events, update agent state.
    Returns (is_allowed, events).
    """
    events = check_action(action, state, campaign_max_cpm, daily_budget)
    state.supervision_events.extend(events)

    # Pause agent if any critical event
    critical = [e for e in events if e.severity == "critical"]
    if critical:
        state.status = "paused"
        return False, events

    # Record safe action
    state.actions.append(action)
    return True, events
