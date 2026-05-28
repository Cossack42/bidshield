"""
BidShield Dashboard — Autonomous Ad Bidding Agent with Brand Safety Gates

Run with: streamlit run dashboard.py
"""
import streamlit as st
import time
from dotenv import load_dotenv

load_dotenv()

from src.models import CampaignBrief, ConversationContext, AgentState, BidStreamResult
from src.contexts import SIMULATED_CONTEXTS
from src import agent, tools

st.set_page_config(
    page_title="BidShield — Autonomous Ad Bidding",
    page_icon="🛡️",
    layout="wide",
)

# ── Custom styling ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1a1d23;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #2d3139;
    }
    .bid-auto { border-left: 4px solid #10b981; padding-left: 12px; margin-bottom: 8px; }
    .bid-escalated { border-left: 4px solid #f59e0b; padding-left: 12px; margin-bottom: 8px; }
    .bid-skipped { border-left: 4px solid #6b7280; padding-left: 12px; margin-bottom: 8px; }
    .bid-blocked { border-left: 4px solid #ef4444; padding-left: 12px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ───────────────────────────────────────────────────────
if "state" not in st.session_state:
    st.session_state.state = AgentState()
if "results" not in st.session_state:
    st.session_state.results = []
if "escalation_queue" not in st.session_state:
    st.session_state.escalation_queue = []
if "stream_running" not in st.session_state:
    st.session_state.stream_running = False
if "stream_complete" not in st.session_state:
    st.session_state.stream_complete = False
if "brief" not in st.session_state:
    st.session_state.brief = None
if "market_context" not in st.session_state:
    st.session_state.market_context = ""


# ── Sidebar: Brand Brief ─────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛡️ BidShield")
    st.caption("Autonomous Ad Bidding Agent")
    st.divider()

    st.subheader("Brand Brief")
    brand_name = st.text_input("Brand Name", "DataPulse Analytics")
    brand_objective = st.text_input(
        "Objective",
        "Drive sign-ups for enterprise analytics platform"
    )
    target_audience = st.text_input(
        "Target Audience",
        "Marketing managers and data leads at mid-market UK B2B companies"
    )
    daily_budget = st.number_input("Daily Budget (£)", value=500.0, step=50.0)
    max_cpm = st.number_input("Max CPM (£)", value=5.0, step=0.5)
    forbidden_topics = st.text_area(
        "Forbidden Topics (one per line)",
        "gambling\nadult content\ncryptocurrency scams\nweapons\ncompetitor bashing"
    )
    tone = st.text_input("Brand Tone", "professional, helpful, data-driven")

    st.divider()

    col1, col2 = st.columns(2)
    start_stream = col1.button(
        "▶ Start Bidding", use_container_width=True, type="primary",
        disabled=st.session_state.stream_running,
    )
    reset = col2.button("↺ Reset", use_container_width=True)

    if reset:
        st.session_state.state = AgentState()
        st.session_state.results = []
        st.session_state.escalation_queue = []
        st.session_state.stream_running = False
        st.session_state.stream_complete = False
        st.session_state.brief = None
        st.session_state.market_context = ""
        st.rerun()

    st.divider()
    st.caption("**Bonus integrations**")
    st.caption("🔍 Tavily — market research")
    st.caption("🛡️ Overmind — supervision layer")
    st.caption("⚡ Built in Cursor")


# ── Main Panel ────────────────────────────────────────────────────────────────
st.title("BidShield")
st.caption("Autonomous ad bidding for LLM conversation channels · Human-in-the-loop for ambiguous placements · Overmind guardrails for safety")

# ── Status banner ─────────────────────────────────────────────────────────────
status_container = st.empty()
agent_state = st.session_state.state

if agent_state.status == "paused":
    status_container.error("🚨 AGENT PAUSED — Overmind detected anomaly. Human review required.")
elif st.session_state.stream_complete:
    status_container.success("✅ Bid stream complete — all contexts processed.")
elif st.session_state.stream_running:
    status_container.info("⏳ Agent running — processing bid stream...")
else:
    status_container.info("Configure your brand brief and click **Start Bidding** to begin.")

# ── Metrics row ───────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
results = st.session_state.results

auto_bids = [r for r in results if r.decision == "auto_bid"]
escalated = [r for r in results if r.decision == "escalated"]
skipped = [r for r in results if r.decision == "skipped"]
blocked = [r for r in results if r.decision == "blocked"]

m1.metric("Auto-Bids", len(auto_bids))
m2.metric("Escalated", len(escalated))
m3.metric("Skipped", len(skipped))
m4.metric("Blocked", len(blocked))
total_spend = sum(r.spend_gbp for r in results)
m5.metric("Spend", f"£{total_spend:.2f} / £{daily_budget:.0f}")

# ── Budget progress bar ───────────────────────────────────────────────────────
budget_pct = min(total_spend / daily_budget, 1.0) if daily_budget > 0 else 0
st.progress(budget_pct, text=f"Budget utilization: {budget_pct*100:.1f}%")

# ── Main content: Bid Stream + Escalation Queue ───────────────────────────────
col_stream, col_escalation = st.columns([3, 2])

with col_stream:
    st.subheader("📡 Bid Stream")
    if not results:
        st.info("No bids yet. Start the agent to see decisions flow in.")
    else:
        for r in reversed(results):
            decision_icon = {
                "auto_bid": "🟢",
                "escalated": "🟡",
                "skipped": "⚪",
                "blocked": "🔴",
            }[r.decision]
            decision_label = {
                "auto_bid": "AUTO-BID",
                "escalated": "ESCALATED",
                "skipped": "SKIPPED",
                "blocked": "BLOCKED",
            }[r.decision]
            css_class = f"bid-{r.decision.replace('_', '-') if r.decision != 'auto_bid' else 'auto'}"

            with st.container():
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<strong>{decision_icon} {decision_label}</strong> · '
                    f'<em>{r.context.channel}</em> · {r.context.topic_category}<br/>'
                    f'"{r.context.user_prompt[:80]}..."<br/>'
                    f'{"Score: " + str(int(r.score.overall_score)) + "/100 · " if r.score else ""}'
                    f'{"£" + f"{r.bid_cpm_gbp:.2f}" + " CPM · " if r.bid_cpm_gbp else ""}'
                    f'{"Spend: £" + f"{r.spend_gbp:.2f}" if r.spend_gbp else ""}'
                    f'{"<br/><em>" + r.score.reasoning + "</em>" if r.score else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

with col_escalation:
    st.subheader("⚠️ Escalation Queue")
    if not st.session_state.escalation_queue:
        st.info("No items pending human review.")
    else:
        for idx, r in enumerate(st.session_state.escalation_queue):
            with st.container(border=True):
                st.markdown(f"**{r.context.channel}** · {r.context.topic_category}")
                st.markdown(f'"{r.context.user_prompt[:100]}"')
                if r.score:
                    st.markdown(
                        f"Score: **{int(r.score.overall_score)}/100** · "
                        f"Relevance: {int(r.score.brand_relevance)} · "
                        f"Risk: {int(r.score.safety_risk)} · "
                        f"Intent: {int(r.score.intent_strength)}"
                    )
                    st.caption(f"💭 {r.score.reasoning}")

                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", key=f"approve_{idx}", use_container_width=True):
                    approved_result = agent.process_escalation(
                        r, True, st.session_state.brief, st.session_state.state
                    )
                    # Move from queue to results
                    st.session_state.escalation_queue.pop(idx)
                    st.session_state.results.append(approved_result)
                    st.rerun()
                if c2.button("❌ Reject", key=f"reject_{idx}", use_container_width=True):
                    rejected_result = agent.process_escalation(
                        r, False, st.session_state.brief, st.session_state.state
                    )
                    st.session_state.escalation_queue.pop(idx)
                    st.session_state.results.append(rejected_result)
                    st.rerun()

# ── Supervision Events Panel ──────────────────────────────────────────────────
if agent_state.supervision_events:
    st.divider()
    st.subheader("🛡️ Overmind Supervision Events")
    for event in reversed(agent_state.supervision_events):
        if event.severity == "critical":
            st.error(f"🚨 **{event.rule_violated.upper()}** — {event.description}")
        elif event.severity == "warning":
            st.warning(f"⚠️ **{event.rule_violated}** — {event.description}")
        else:
            st.info(event.description)

# ── Run the bid stream ────────────────────────────────────────────────────────
if start_stream:
    # Build brief from form
    brief = CampaignBrief(
        brand=brand_name,
        objective=brand_objective,
        target_audience=target_audience,
        daily_budget_gbp=daily_budget,
        max_cpm_gbp=max_cpm,
        forbidden_topics=[t.strip() for t in forbidden_topics.split("\n") if t.strip()],
        tone=tone,
    )
    st.session_state.brief = brief
    st.session_state.state = AgentState(budget_remaining_gbp=daily_budget)
    st.session_state.results = []
    st.session_state.escalation_queue = []
    st.session_state.stream_running = True
    st.session_state.stream_complete = False

    # Step 1: Tavily market research
    with st.spinner("🔍 Tavily: Researching market context..."):
        try:
            market_context = tools.research_market_context(
                f"{brand_objective} {target_audience} advertising UK 2025"
            )
            st.session_state.market_context = market_context
        except Exception as e:
            st.warning(f"Tavily research skipped: {e}")
            market_context = ""

    # Step 2: Process each context
    contexts = [ConversationContext(**c) for c in SIMULATED_CONTEXTS]

    progress_bar = st.progress(0, text="Processing bid stream...")

    for i, ctx in enumerate(contexts):
        if st.session_state.state.status == "paused":
            break

        progress_bar.progress(
            (i + 1) / len(contexts),
            text=f"Processing {i+1}/{len(contexts)}: {ctx.topic_category}..."
        )

        try:
            result = agent.process_context(
                ctx, brief, st.session_state.state, market_context
            )
        except Exception as e:
            st.error(f"Error processing context {ctx.id}: {e}")
            continue

        if result.decision == "escalated":
            st.session_state.escalation_queue.append(result)
        else:
            st.session_state.results.append(result)

        # Small delay for dramatic effect
        time.sleep(0.3)

    st.session_state.stream_running = False
    st.session_state.stream_complete = True
    progress_bar.empty()
    st.rerun()
