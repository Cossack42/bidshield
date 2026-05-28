# BidShield — Autonomous Ad Bidding Agent

> Built at the Cursor x Thrad London Hackathon, 28 May 2026
> Track 1: Buy-Side Agents

An AI agent that autonomously bids on ad placements in LLM conversation channels — auto-approving safe matches, escalating ambiguous ones to a human, and halting when brand safety is at risk. Powered by **Overmind** supervision, **Tavily** market research, and **Claude** decision-making.

**The thesis:** You can't let an ad bidding agent spend money unsupervised. BidShield shows the three-tier gate that makes autonomous bidding safe: auto-bid, escalate, or block.

---

## Quick Start

```bash
cd ~/Desktop/cursor-adtech-hackathon
source .venv/bin/activate
pip install -r requirements.txt

# Set up .env with your ANTHROPIC_API_KEY and TAVILY_API_KEY
streamlit run dashboard.py
```

## Demo Flow (90 seconds)

1. Pre-filled brand brief loads (DataPulse Analytics)
2. Click **Start Bidding** — 10 conversation contexts stream in
3. Watch auto-bids (green), escalations (yellow), skips (grey)
4. Approve/reject escalated items in the human queue
5. See Overmind fire on the dangerous placement (red alert, agent pauses)
6. Budget tracker shows spend stayed under cap

## Architecture

```
Tavily (market research) → Claude (scoring + creative) → Overmind (guardrails)
                                    ↓
                    ┌───────────────────────────────┐
                    │  score >= 80  → AUTO-BID      │
                    │  40-79        → ESCALATE      │
                    │  < 40 or risky → SKIP/BLOCK   │
                    └───────────────────────────────┘
```

## Judging Alignment

| Criterion | How we address it |
|-----------|------------------|
| Concrete Workflow Value | Replaces manual media buying decisions |
| Track Fit | Pure buy-side: brand brief → bid → creative → guardrails |
| Human-in-the-Loop | Three-tier gate with explicit escalation queue |
| Technical Execution | Claude + Tavily + Overmind integrated end-to-end |
| Demo Clarity | 90-second flow, visible decisions, dramatic anomaly |
