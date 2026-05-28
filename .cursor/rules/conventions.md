---
description: "Core conventions for the BidShield hackathon project"
alwaysApply: true
---

# Project: BidShield — Autonomous Ad Bidding Agent

## What this project does
An autonomous AI agent that bids on ad placements in LLM conversation channels.
It scores each conversation context for brand fit, safety, and intent, then makes
a three-tier decision: auto-bid (safe + relevant), escalate (ambiguous, human decides),
or skip/block (off-brand or dangerous). Overmind supervision checks every action.

Demo flow: brand brief → bid stream → auto decisions + escalations + anomaly catch.

## Tech stack
- Python 3.11+
- Streamlit for the dashboard UI (do NOT suggest React/Next.js — we need speed)
- Anthropic SDK (`anthropic`) for Claude — use `claude-haiku-4-5-20251001` for speed
- Tavily Python SDK (`tavily-python`) for market research
- Pydantic v2 for all data models — never use raw dicts for structured data
- python-dotenv for env vars

## File layout
- `dashboard.py` — Streamlit entry point, run with `streamlit run dashboard.py`
- `src/agent.py` — core agent: score_context(), decide_bid(), generate_creative(), process_context()
- `src/supervisor.py` — Overmind supervision layer (guardrail checks)
- `src/tools.py` — Tavily search tools
- `src/models.py` — all Pydantic models
- `src/contexts.py` — simulated conversation contexts (ad opportunities)
- `SPEC.md` — full architecture spec and build plan
- `.env` — API keys (never commit this)

## Code conventions
- All bid actions MUST go through `supervisor.apply_supervision()` before being recorded
- Pydantic models for all data — no raw dicts passed between functions
- Functions return typed values, not print statements
- Keep agent.py and supervisor.py decoupled — supervisor never imports from agent
- Error messages must be user-facing friendly (shown in Streamlit UI)
- Three-tier decision gate: auto_bid (>=80), escalated (40-79), skipped (<40 or risky)

## What NOT to do
- Do NOT use FastAPI/Flask — we're using Streamlit only
- Do NOT use async — Streamlit doesn't play well with asyncio in hackathon context
- Do NOT add a database — in-memory state via st.session_state is fine
- Do NOT hardcode API keys — always read from os.getenv()
- Do NOT change the SupervisionEvent/CampaignAction models without updating dashboard rendering

## Demo requirements
- Pre-filled brand brief must work out of the box (DataPulse Analytics)
- Bid stream must show at least 10 contexts with mixed decisions
- Escalation queue must have approve/reject buttons that work
- Overmind must fire a critical alert on at least one context
- Budget progress bar must be visible and accurate
- 90-second demo must be possible without any typing

## Models in use
- `claude-haiku-4-5-20251001` — fast, cheap, used for all scoring and creative
- Tavily free tier — use basic search_depth to conserve credits
