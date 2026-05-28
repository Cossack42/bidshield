"""
Dynamic conversation context generation — Claude generates realistic
ad opportunities tailored to whatever brand brief the user enters.
"""
import json
import random
from src.models import CampaignBrief


CHANNELS = ["ChatGPT", "Claude", "Perplexity", "Custom chatbot", "Gemini"]


def generate_contexts(brief: CampaignBrief, ask_claude_fn, count: int = 10) -> list[dict]:
    """Generate realistic conversation contexts based on the brand brief."""

    prompt = f"""You are simulating an ad exchange feed for LLM conversation channels.

BRAND BRIEF (the advertiser):
- Brand: {brief.brand}
- Objective: {brief.objective}
- Target audience: {brief.target_audience}
- Forbidden topics: {', '.join(brief.forbidden_topics)}

Generate exactly {count} user prompts that represent real conversations happening across ChatGPT, Claude, Perplexity, and other LLM chatbots RIGHT NOW. These are ad placement opportunities — the brand can bid to show a sponsored answer.

The mix MUST be:
- 3-4 that are PERFECT fits (high relevance, safe, strong purchase intent)
- 2-3 that are AMBIGUOUS (moderate fit, or some risk like competitor mentions, adjacent but not exact category)
- 2 that are CLEARLY OFF-BRAND (wrong audience, wrong category entirely)
- 1 that hits a FORBIDDEN TOPIC (from the list above)
- 1 that is a BUDGET TRAP — perfect relevance but absurdly high volume (200000+ impressions) that would blow any reasonable budget

Each prompt should sound like a real person typing into a chatbot — natural, specific, with real details.

Return ONLY a valid JSON array:
[
  {{
    "user_prompt": "the actual question the user typed",
    "topic_category": "short label like 'B2B software' or 'Personal finance'",
    "estimated_impressions": 3000-200000,
    "floor_cpm_gbp": 0.40-8.00
  }},
  ...
]

Rules:
- Vary the impressions realistically (niche queries = 3000-8000, broad queries = 15000-50000, the budget trap = 200000+)
- Floor CPM should reflect value (high-intent enterprise = £3-5, casual browsing = £0.40-1.50, the budget trap = £6+)
- Make prompts specific and detailed, not generic
- Include real product names, company sizes, budgets where relevant
- The forbidden topic one should clearly match one of: {', '.join(brief.forbidden_topics)}"""

    text = ask_claude_fn(prompt, model="claude-sonnet-4-6", max_tokens=2000)
    data = _extract_json_array(text)

    contexts = []
    for i, item in enumerate(data[:count]):
        contexts.append({
            "id": f"ctx-{i+1:03d}",
            "user_prompt": item["user_prompt"],
            "channel": random.choice(CHANNELS),
            "topic_category": item["topic_category"],
            "estimated_impressions": item["estimated_impressions"],
            "floor_cpm_gbp": item["floor_cpm_gbp"],
        })

    return contexts


def _extract_json_array(text: str) -> list:
    """Extract a JSON array from Claude's response."""
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
