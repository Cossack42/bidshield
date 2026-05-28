"""
Overmind supervision layer.

Checks every agent action against guardrails before it's committed.
When the real Overmind SDK is available, replace mock with actual SDK calls.
"""
from src.models import CampaignAction, SupervisionEvent, AgentState


PROHIBITED_KEYWORDS = [
    "guaranteed returns", "risk-free", "casino", "crypto guaranteed",
    "weight loss miracle", "cure", "unlimited money",
]


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
        impressions = action.value.get("estimated_impressions", 1000)
        estimated_spend = cpm * impressions / 1000

        # Rule 1: CPM ceiling (3x max)
        if cpm > campaign_max_cpm * 3:
            events.append(SupervisionEvent(
                severity="critical",
                rule_violated="max_cpm_ceiling",
                description=f"CPM £{cpm:.2f} exceeds 3x campaign ceiling (£{campaign_max_cpm * 3:.2f}). Agent halted.",
                action_id=action.id,
                agent_paused=True,
            ))

        # Rule 2: Budget exhaustion — would this bid blow the daily budget?
        if state.total_spend_gbp + estimated_spend > daily_budget:
            events.append(SupervisionEvent(
                severity="critical",
                rule_violated="budget_exhaustion",
                description=f"Bid would push spend to £{state.total_spend_gbp + estimated_spend:.2f}, exceeding daily budget of £{daily_budget:.2f}. Agent halted.",
                action_id=action.id,
                agent_paused=True,
            ))

        # Rule 3: Budget spike — single bid > 40% of daily budget (warning only)
        if estimated_spend > daily_budget * 0.40:
            events.append(SupervisionEvent(
                severity="warning",
                rule_violated="budget_spike",
                description=f"Single bid spend £{estimated_spend:.2f} is {estimated_spend/daily_budget*100:.0f}% of daily budget.",
                action_id=action.id,
                agent_paused=False,
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

    critical = [e for e in events if e.severity == "critical"]
    if critical:
        state.status = "paused"
        return False, events

    state.actions.append(action)
    return True, events
