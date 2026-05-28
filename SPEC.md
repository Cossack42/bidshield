# BidShield — Build Spec & Architecture

> Autonomous Ad Bidding Agent with Brand Safety Gates
> Cursor x Thrad Hackathon · London · 28 May 2026
> Track 1: Buy-Side Agents

---

## One-liner

An AI agent that autonomously bids on ad placements in LLM conversations — auto-approving safe matches, escalating ambiguous ones to a human, and halting when brand safety is at risk.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   STREAMLIT DASHBOARD                    │
│                                                         │
│  ┌───────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │  Brand    │  │  Live Bid     │  │  Budget &      │  │
│  │  Brief    │  │  Stream       │  │  Analytics     │  │
│  │  + Safety │  │  (real-time)  │  │  (chart+stats) │  │
│  └───────────┘  └───────┬───────┘  └────────────────┘  │
│                         │                               │
│  ┌──────────────────────▼────────────────────────────┐  │
│  │          HUMAN ESCALATION QUEUE                   │  │
│  │   [Approve] [Reject] for ambiguous placements     │  │
│  └───────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────┘
                            │
          ┌─────────────────▼───────────────────┐
          │          AGENT CORE                  │
          │                                     │
          │  For each conversation context:     │
          │                                     │
          │  1. Tavily enriches context with    │
          │     live market data                │
          │                                     │
          │  2. Claude scores context:          │
          │     - Brand relevance (0-100)       │
          │     - Safety risk (0-100)           │
          │     - Intent strength (0-100)       │
          │                                     │
          │  3. Decision gate:                  │
          │     score >= 80 → AUTO-BID          │
          │     40-79     → ESCALATE to human   │
          │     < 40      → AUTO-SKIP           │
          │                                     │
          │  4. If bidding: Claude generates    │
          │     creative for the placement      │
          │                                     │
          └─────────────────┬───────────────────┘
                            │
          ┌─────────────────▼───────────────────┐
          │      OVERMIND SUPERVISION LAYER      │
          │                                     │
          │  Checks EVERY action before commit: │
          │  • CPM ceiling (3x max = critical)  │
          │  • Budget spike (>20% daily)        │
          │  • Forbidden topic detection        │
          │  • Content policy scan              │
          │  • Bid drift (3 consecutive highs)  │
          │                                     │
          │  CRITICAL → agent paused            │
          │  WARNING  → logged, continues       │
          └─────────────────────────────────────┘
```

---

## Demo Flow (90 seconds)

1. **0-15s**: "BidShield bids on ad placements in LLM conversations. Give it a brand brief, it handles the rest."
2. **15-30s**: Pre-filled brief loads. Click "Start Bid Stream". 3-4 placements auto-bid (green).
3. **30-50s**: Ambiguous placement hits escalation queue. Click Approve → agent bids.
4. **50-70s**: Dangerous placement (competitor + high CPM). Overmind fires. Agent pauses. Red alert.
5. **70-90s**: "6 autonomous decisions, 2 escalated, 1 anomaly caught. Budget stayed under cap."

---

## File Structure

```
cursor-adtech-hackathon/
├── dashboard.py          # Streamlit UI — bid stream, escalation queue, budget chart
├── src/
│   ├── __init__.py
│   ├── models.py         # Pydantic models (CampaignBrief, BidStreamResult, etc.)
│   ├── agent.py          # Core agent loop — scores contexts, makes bid decisions
│   ├── supervisor.py     # Overmind guardrails — checks every action
│   ├── tools.py          # Tavily integration for context enrichment
│   └── contexts.py       # Simulated conversation contexts (ad opportunities)
├── .env                  # API keys (never commit)
├── .env.example
├── requirements.txt
├── SPEC.md               # This file
└── README.md             # Quick setup + demo instructions
```

---

## Models (src/models.py)

```python
class CampaignBrief:
    brand: str
    objective: str
    target_audience: str
    daily_budget_gbp: float
    max_cpm_gbp: float
    forbidden_topics: list[str]          # NEW — brand safety blacklist
    tone: str                            # NEW — e.g. "professional, helpful"

class ConversationContext:               # NEW — represents an ad opportunity
    id: str
    user_prompt: str                     # what the user asked in the LLM
    channel: str                         # e.g. "ChatGPT", "Claude", "Custom chatbot"
    topic_category: str                  # e.g. "B2B software", "travel", "finance"
    estimated_impressions: int
    floor_cpm_gbp: float                 # minimum bid to win

class ContextScore:                      # NEW — Claude's evaluation
    context_id: str
    brand_relevance: float               # 0-100
    safety_risk: float                   # 0-100 (high = dangerous)
    intent_strength: float               # 0-100
    overall_score: float                 # weighted composite
    reasoning: str

class BidStreamResult:                   # NEW — outcome of one bid decision
    context: ConversationContext
    score: ContextScore
    decision: Literal["auto_bid", "escalated", "skipped", "blocked"]
    bid_cpm_gbp: float | None
    creative: AdCreative | None
    supervision_events: list[SupervisionEvent]
    human_approved: bool | None          # None if not escalated

# Keep existing: AdCreative, BidDecision, CampaignAction, SupervisionEvent, AgentState
```

---

## Simulated Contexts (src/contexts.py)

10 conversation contexts — mix of:
- 4 clearly relevant (high brand fit, safe) → auto-bid
- 3 ambiguous (moderate fit, some risk) → escalate
- 2 off-brand or forbidden topic → auto-skip
- 1 dangerous (competitor + extreme CPM) → triggers Overmind critical alert

Example contexts for a "B2B SaaS analytics" brand:
1. "What's the best analytics tool for a 50-person marketing team?" → HIGH FIT
2. "Compare Mixpanel vs Amplitude for product analytics" → COMPETITOR MENTION → skip/escalate
3. "I need help with my gambling addiction" → FORBIDDEN → skip
4. "Best project management software for remote teams?" → MODERATE FIT → escalate
5. "How do I set up Google Analytics 4 tracking?" → HIGH FIT
6. "What CRM integrates with analytics dashboards?" → HIGH FIT
7. "Best free tools for data visualization?" → LOW BUDGET INTENT → skip
8. "Enterprise analytics for financial services compliance" → HIGH FIT, HIGH VALUE
9. "I want to switch from [competitor] to something better" → COMPETITOR but HIGH INTENT → escalate
10. "Need analytics + unlimited seats + under £10/month" → BUDGET MISMATCH + HIGH VOLUME → Overmind triggers (CPM spike attempt)

---

## Agent Logic (src/agent.py)

### score_context(context, brief) → ContextScore
- Calls Claude with the context + brand brief
- Returns structured JSON score (relevance, safety, intent)
- Checks forbidden_topics locally first (fast reject before LLM call)

### decide_bid(score, brief) → decision
- score.overall >= 80 → "auto_bid"
- 40 <= score.overall < 80 → "escalated"
- score.overall < 40 → "skipped"
- safety_risk > 70 → always "skipped" regardless of relevance

### generate_creative(context, brief) → AdCreative
- Only called when decision is "auto_bid" or human approves escalation
- Claude generates a conversational ad (headline, body, CTA)
- Fitted to the specific conversation context

### run_bid_stream(brief, contexts) → list[BidStreamResult]
- Main loop: iterate through contexts
- For each: score → decide → supervise → (optional) generate creative
- Yields results one at a time for streaming UI

---

## Dashboard (dashboard.py)

### Layout:
```
┌─────────────────────────────────────────────────────────────┐
│  BIDSHIELD — Autonomous Ad Bidding Agent                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  SIDEBAR:                    MAIN AREA:                     │
│  ┌──────────────┐           ┌─────────────────────────────┐ │
│  │ Brand Brief  │           │ Status Banner (green/red)   │ │
│  │ - Objective  │           ├─────────────────────────────┤ │
│  │ - Audience   │           │                             │ │
│  │ - Budget     │           │ BID STREAM                  │ │
│  │ - Max CPM    │           │ [context] → [score] → [bid] │ │
│  │ - Forbidden  │           │ [context] → [score] → [skip]│ │
│  │   topics     │           │ [context] → [escalated] ⏳  │ │
│  │ - Tone       │           │                             │ │
│  │              │           ├─────────────────────────────┤ │
│  │ [Start]      │           │ ESCALATION QUEUE            │ │
│  │ [Reset]      │           │ "CRM + analytics" — 65/100  │ │
│  └──────────────┘           │ [Approve] [Reject]          │ │
│                             ├─────────────────────────────┤ │
│                             │ METRICS        │ BUDGET     │ │
│                             │ Auto-bids: 4   │ ████░░ 62% │ │
│                             │ Escalated: 2   │ £310/£500  │ │
│                             │ Skipped: 3     │            │ │
│                             │ Blocked: 1     │            │ │
│                             └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Key UI behaviors:
- Bid stream results appear one-by-one with slight delay (dramatic effect)
- Color coding: green=auto-bid, yellow=escalated, red=blocked, grey=skipped
- Escalation queue shows pending items with approve/reject buttons
- Budget bar fills up as bids are placed
- Overmind alert is a full-width red banner that interrupts everything

---

## Scoring Rubric Alignment

| Criterion (pts) | How BidShield scores |
|-----------------|---------------------|
| Concrete Workflow Value (2) | Replaces manual campaign management — media buyers do this daily |
| Track Fit (2) | Pure buy-side: brand brief → bid → creative → guardrails |
| Human-in-the-Loop (1) | Explicit 3-tier gate: auto/escalate/block. Human approves ambiguous bids |
| Technical Execution (1) | Claude + Tavily + Overmind integrated. Clean architecture, live demo |
| Demo Clarity (1) | 90-second script, visible decisions, dramatic anomaly catch |

## Bonus Points

| Bonus (1pt each) | Strategy |
|------------------|----------|
| Tavily | Market research enriches every context score — show "Tavily" badge in UI |
| Overmind | Supervision layer is the safety net — show Overmind logo on alerts |
| Cursor | Built entirely in Cursor. Mention Composer 2.5 in submission |
| Alpic | Stretch goal. Skip if time is tight |

---

## Implementation Order (for Cursor)

1. `src/contexts.py` — write the 10 simulated contexts (5 min)
2. `src/models.py` — add new models (ConversationContext, ContextScore, BidStreamResult, update CampaignBrief) (5 min)
3. `src/agent.py` — rewrite: score_context(), decide_bid(), generate_creative(), run_bid_stream() (20 min)
4. `src/supervisor.py` — add forbidden_topics checking (5 min)
5. `dashboard.py` — full UI rebuild: bid stream, escalation queue, budget chart (30 min)
6. Polish: colors, timing, pre-filled defaults, error handling (15 min)
7. Test full demo flow end-to-end (10 min)
8. README update for submission (5 min)

**Total: ~95 min** (leaves 10 min buffer from 1h45m)
