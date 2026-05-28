"""
CLI runner for BidShield — runs the full bid stream with logging.
Usage: python run.py
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from src.models import CampaignBrief, ConversationContext, AgentState
from src.contexts import generate_contexts
from src import agent, tools


def main():
    brief = CampaignBrief(
        brand="Helix Fitness",
        objective="Drive app downloads and premium subscriptions for AI personal training app",
        target_audience="Health-conscious professionals aged 25-45 looking for personalized workout plans",
        daily_budget_gbp=500.0,
        max_cpm_gbp=5.0,
        forbidden_topics=["eating disorders", "steroids", "weight loss pills", "gambling"],
        tone="motivating, friendly, science-backed",
    )
    state = AgentState(budget_remaining_gbp=500.0)

    print(f"=== BidShield Run ===")
    print(f"Brand: {brief.brand}")
    print(f"Budget: £{brief.daily_budget_gbp} | Max CPM: £{brief.max_cpm_gbp}")
    print()

    # Tavily research
    print("[TAVILY] Researching market context...")
    try:
        market_context = tools.research_market_context(
            f"{brief.objective} {brief.target_audience} advertising UK 2025"
        )
        print(f"[TAVILY] OK — {len(market_context)} chars")
    except Exception as e:
        print(f"[TAVILY] FAILED — {e}")
        market_context = ""
    print()

    # Generate dynamic contexts
    print("[CONTEXTS] Generating ad opportunities for this brand...")
    raw_contexts = generate_contexts(brief, agent.ask_claude)
    print(f"[CONTEXTS] Generated {len(raw_contexts)} contexts")
    print()

    contexts = [ConversationContext(**c) for c in raw_contexts]
    results = []
    escalated = []

    for i, ctx in enumerate(contexts):
        print(f"--- Context {i+1}/{len(contexts)}: {ctx.id} ({ctx.topic_category}) ---")
        print(f"  Prompt: {ctx.user_prompt[:80]}")
        print(f"  Channel: {ctx.channel} | Impressions: {ctx.estimated_impressions:,} | Floor: £{ctx.floor_cpm_gbp}")

        if state.status == "paused":
            print(f"  [SKIP] Agent is paused — skipping remaining contexts")
            break

        try:
            result = agent.process_context(ctx, brief, state, market_context)
        except Exception as e:
            print(f"  [ERROR] {e}")
            continue

        print(f"  Score: {int(result.score.overall_score) if result.score else 'N/A'}/100")
        if result.score:
            print(f"    Relevance: {int(result.score.brand_relevance)} | Risk: {int(result.score.safety_risk)} | Intent: {int(result.score.intent_strength)}")
            print(f"    Reasoning: {result.score.reasoning}")
        print(f"  Decision: {result.decision.upper()}")

        if result.bid_cpm_gbp is not None:
            print(f"  Bid: £{result.bid_cpm_gbp:.2f} CPM | Spend: £{result.spend_gbp:.2f}")
        if result.creative:
            print(f"  Creative: {result.creative.headline}")

        for ev in result.supervision_events:
            print(f"  [{ev.severity.upper()}] {ev.rule_violated}: {ev.description}")

        if result.decision == "escalated":
            escalated.append(result)
        else:
            results.append(result)

        print(f"  Running total: £{state.total_spend_gbp:.2f} / £{brief.daily_budget_gbp:.2f}")
        print()

    # Summary
    print("=== SUMMARY ===")
    all_results = results + escalated
    print(f"Auto-bids:  {sum(1 for r in results if r.decision == 'auto_bid')}")
    print(f"Escalated:  {len(escalated)}")
    print(f"Skipped:    {sum(1 for r in results if r.decision == 'skipped')}")
    print(f"Blocked:    {sum(1 for r in results if r.decision == 'blocked')}")
    print(f"Total spend: £{state.total_spend_gbp:.2f} / £{brief.daily_budget_gbp:.2f}")
    print(f"Agent status: {state.status}")
    print(f"Supervision events: {len(state.supervision_events)}")
    for ev in state.supervision_events:
        print(f"  [{ev.severity.upper()}] {ev.rule_violated}: {ev.description}")


if __name__ == "__main__":
    main()
