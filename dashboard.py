"""
BidShield Dashboard — Autonomous Ad Bidding Agent with Brand Safety Gates

Run with: streamlit run dashboard.py
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.models import CampaignBrief, ConversationContext, AgentState, BidStreamResult
from src.contexts import generate_contexts
from src import agent, tools

st.set_page_config(
    page_title="BidShield",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

    /* ── Base ─────────────────────────────────────────── */
    .stApp {
        background-color: #08090c;
        font-family: 'DM Sans', sans-serif;
    }
    header[data-testid="stHeader"] { background: transparent; }
    section[data-testid="stSidebar"] {
        background-color: #0d0f14;
        border-right: 1px solid #1a1d25;
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown label,
    section[data-testid="stSidebar"] .stTextInput label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stTextArea label {
        font-family: 'DM Sans', sans-serif;
        color: #8b8fa3;
        font-size: 0.82rem;
        letter-spacing: 0.02em;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea {
        background-color: #12141b !important;
        border: 1px solid #1e2130 !important;
        color: #c8cad4 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.85rem !important;
        border-radius: 6px !important;
    }
    section[data-testid="stSidebar"] input:focus,
    section[data-testid="stSidebar"] textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 1px #3b82f620 !important;
    }

    /* ── Sidebar number inputs ────────────────────────── */
    section[data-testid="stSidebar"] .stNumberInput input {
        min-width: 0 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebar"] {
        min-width: 280px;
    }

    /* ── Metrics ──────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #0f1118 0%, #12141d 100%);
        border: 1px solid #1a1d28;
        border-radius: 10px;
        padding: 16px 18px;
    }
    div[data-testid="stMetric"] label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #5a5e72 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.5rem !important;
        font-weight: 700;
        color: #e2e4ed !important;
    }

    /* ── Progress bar ─────────────────────────────────── */
    div[data-testid="stProgress"] > div > div {
        background-color: #1a1d28 !important;
        border-radius: 4px;
    }
    div[data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, #3b82f6, #6366f1) !important;
        border-radius: 4px;
    }

    /* ── Buttons ──────────────────────────────────────── */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        font-size: 0.85rem;
        letter-spacing: 0.01em;
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
        border: none !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px #3b82f630;
    }

    /* ── Alerts ───────────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: 8px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.85rem;
    }

    /* ── Containers ───────────────────────────────────── */
    div[data-testid="stContainer"] {
        border-radius: 10px !important;
    }

    /* ── Dividers ─────────────────────────────────────── */
    hr { border-color: #1a1d28 !important; }

    /* ── Hide Streamlit chrome ────────────────────────── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    div[data-testid="stDecoration"] { display: none; }

    /* ── Custom bid cards ─────────────────────────────── */
    .bid-card {
        background: #0d0f16;
        border: 1px solid #1a1d28;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 10px;
        transition: border-color 0.2s ease;
    }
    .bid-card:hover { border-color: #2a2d3a; }
    .bid-card--auto { border-left: 3px solid #10b981; }
    .bid-card--escalated { border-left: 3px solid #f59e0b; }
    .bid-card--skipped { border-left: 3px solid #3a3d4a; }
    .bid-card--blocked { border-left: 3px solid #ef4444; }

    .bid-decision {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        margin-bottom: 6px;
    }
    .bid-decision--auto { background: #10b98118; color: #34d399; }
    .bid-decision--escalated { background: #f59e0b18; color: #fbbf24; }
    .bid-decision--skipped { background: #6b728018; color: #9ca3af; }
    .bid-decision--blocked { background: #ef444418; color: #f87171; }

    .bid-prompt {
        color: #b0b3c4;
        font-size: 0.88rem;
        line-height: 1.45;
        margin: 6px 0;
    }
    .bid-meta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #5a5e72;
        margin-top: 6px;
    }
    .bid-meta span { margin-right: 14px; }
    .bid-meta .score-val { color: #818cf8; }
    .bid-meta .cpm-val { color: #34d399; }
    .bid-meta .spend-val { color: #fbbf24; }
    .bid-reasoning {
        font-size: 0.78rem;
        color: #4a4e62;
        font-style: italic;
        margin-top: 4px;
    }
    .bid-channel {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #4a4e62;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* ── Escalation card ──────────────────────────────── */
    .esc-card {
        background: #11131a;
        border: 1px solid #2a2520;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 10px;
    }
    .esc-scores {
        display: flex;
        gap: 12px;
        margin: 8px 0;
    }
    .esc-score-pill {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        background: #1a1d28;
        padding: 3px 10px;
        border-radius: 20px;
        color: #8b8fa3;
    }

    /* ── Supervision event ────────────────────────────── */
    .sup-event {
        background: #0d0f16;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .sup-event--critical {
        border: 1px solid #ef444440;
        background: #ef44440a;
    }
    .sup-event--warning {
        border: 1px solid #f59e0b30;
        background: #f59e0b08;
    }
    .sup-event-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .sup-event-label--critical { color: #f87171; }
    .sup-event-label--warning { color: #fbbf24; }
    .sup-event-desc {
        color: #8b8fa3;
        font-size: 0.82rem;
        margin-top: 4px;
    }

    /* ── Header ───────────────────────────────────────── */
    .shield-header {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin-bottom: 4px;
    }
    .shield-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.6rem;
        font-weight: 700;
        color: #e2e4ed;
        letter-spacing: -0.02em;
    }
    .shield-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #3b82f6;
        background: #3b82f612;
        padding: 3px 10px;
        border-radius: 4px;
        border: 1px solid #3b82f625;
    }
    .shield-sub {
        font-size: 0.82rem;
        color: #4a4e62;
        margin-bottom: 20px;
        letter-spacing: 0.01em;
    }

    /* ── Section headers ──────────────────────────────── */
    .section-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #5a5e72;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1a1d28;
    }

    /* ── Sidebar branding ─────────────────────────────── */
    .sidebar-brand {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.2rem;
        font-weight: 700;
        color: #e2e4ed;
        letter-spacing: -0.02em;
    }
    .sidebar-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #3b82f6;
        margin-top: 2px;
    }
    .sidebar-integrations {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #3a3d4a;
        line-height: 1.8;
    }
    .sidebar-integrations span {
        color: #5a5e72;
    }
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


# ── Brand presets ─────────────────────────────────────────────────────────────
BRAND_PRESETS = {
    "DataPulse Analytics": {
        "objective": "Drive sign-ups for enterprise analytics platform",
        "audience": "Marketing managers and data leads at mid-market UK B2B companies",
        "forbidden": "gambling\nadult content\ncryptocurrency scams\nweapons",
        "tone": "professional, helpful, data-driven",
    },
    "Helix Fitness": {
        "objective": "Drive app downloads and premium subscriptions for AI personal training app",
        "audience": "Health-conscious professionals aged 25-45 looking for personalized workout plans",
        "forbidden": "eating disorders\nsteroids\nweight loss pills\ngambling",
        "tone": "motivating, friendly, science-backed",
    },
    "NomadDesk": {
        "objective": "Grow waitlist for co-working space marketplace for remote workers",
        "audience": "Digital nomads, freelancers, and remote startup teams looking for flexible workspace",
        "forbidden": "adult content\ngambling\nweapons\npolitical extremism",
        "tone": "casual, adventurous, community-driven",
    },
    "Custom": {
        "objective": "",
        "audience": "",
        "forbidden": "gambling\nadult content\ncryptocurrency scams\nweapons",
        "tone": "professional",
    },
}

# ── Sidebar: Brand Brief ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🛡️ BidShield</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-tag">Autonomous Ad Bidding</div>', unsafe_allow_html=True)
    st.markdown("---")

    preset = st.selectbox("Brand Preset", list(BRAND_PRESETS.keys()))
    p = BRAND_PRESETS[preset]

    brand_name = st.text_input("Brand", preset if preset != "Custom" else "")
    brand_objective = st.text_input("Objective", p["objective"])
    target_audience = st.text_input("Target Audience", p["audience"])

    daily_budget = st.number_input("Daily Budget (£)", value=500.0, step=50.0)
    max_cpm = st.number_input("Max CPM (£)", value=5.0, step=0.5)

    forbidden_topics = st.text_area(
        "Forbidden Topics",
        p["forbidden"],
        height=100,
    )
    tone = st.text_input("Tone", p["tone"])

    st.markdown("---")

    col1, col2 = st.columns(2)
    start_stream = col1.button(
        "▶ Start", use_container_width=True, type="primary",
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

    st.markdown("---")
    st.markdown(
        '<div class="sidebar-integrations">'
        '<span>INTEGRATIONS</span><br/>'
        '🔍 Tavily — market research<br/>'
        '🛡️ Overmind — supervision<br/>'
        '⚡ Cursor — built with'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main Panel ────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="shield-header">'
    '<span class="shield-title">BidShield</span>'
    '<span class="shield-badge">Track 01 · Buy-Side</span>'
    '</div>'
    '<div class="shield-sub">Autonomous bidding on LLM conversation placements · Human-in-the-loop escalation · Overmind guardrails</div>',
    unsafe_allow_html=True,
)

# ── Status banner ─────────────────────────────────────────────────────────────
status_container = st.empty()
agent_state = st.session_state.state

if agent_state.status == "paused":
    status_container.error("🚨 AGENT PAUSED — Overmind detected critical anomaly. Human review required.")
elif st.session_state.stream_complete:
    status_container.success("✅ Bid stream complete — all contexts processed.")
elif st.session_state.stream_running:
    status_container.info("⏳ Processing bid stream...")

# ── Metrics row ───────────────────────────────────────────────────────────────
results = st.session_state.results
auto_bids = [r for r in results if r.decision == "auto_bid"]
escalated_items = [r for r in results if r.decision == "escalated"]
skipped_items = [r for r in results if r.decision == "skipped"]
blocked_items = [r for r in results if r.decision == "blocked"]
total_spend = sum(r.spend_gbp for r in results)

all_evaluated = len(results) + len(st.session_state.escalation_queue)
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("EVALUATED", all_evaluated)
m2.metric("AUTO-BIDS", len(auto_bids))
m3.metric("ESCALATED", len(escalated_items) + len(st.session_state.escalation_queue))
m4.metric("SKIPPED", len(skipped_items))
m5.metric("BLOCKED", len(blocked_items))
m6.metric("SPEND", f"£{total_spend:.2f}")

# ── Budget bar ────────────────────────────────────────────────────────────────
budget_pct = min(total_spend / daily_budget, 1.0) if daily_budget > 0 else 0
st.progress(budget_pct, text=f"Budget: £{total_spend:.2f} / £{daily_budget:.0f}  ·  {budget_pct*100:.0f}%")

# ── Tavily Research Panel ─────────────────────────────────────────────────────
if st.session_state.market_context:
    with st.expander("🔍 Tavily Market Research", expanded=False):
        st.markdown(
            f'<div style="font-family:JetBrains Mono,monospace; font-size:0.72rem; '
            f'color:#8b8fa3; line-height:1.6; white-space:pre-wrap;">'
            f'{st.session_state.market_context[:2000]}'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Source: Tavily Search API · {len(st.session_state.market_context):,} chars · used to enrich context scoring")

# ── Main content ──────────────────────────────────────────────────────────────
col_stream, col_right = st.columns([3, 2])

# ── Bid Stream ────────────────────────────────────────────────────────────────
with col_stream:
    st.markdown('<div class="section-label">📡 Bid Stream</div>', unsafe_allow_html=True)

    if not results and not st.session_state.stream_running:
        st.markdown(
            '<div style="color:#3a3d4a; font-size:0.85rem; padding:40px 0; text-align:center;">'
            'Configure brand brief → Start bidding<br/>'
            '<span style="font-size:0.75rem;">10 conversation contexts will be evaluated</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for r in reversed(results):
            decision_map = {
                "auto_bid": ("AUTO-BID", "auto"),
                "escalated": ("ESCALATED", "escalated"),
                "skipped": ("SKIPPED", "skipped"),
                "blocked": ("BLOCKED", "blocked"),
            }
            label, css = decision_map[r.decision]

            meta_parts = []
            if r.score:
                meta_parts.append(f'<span class="score-val">{int(r.score.overall_score)}/100</span>')
            if r.bid_cpm_gbp:
                meta_parts.append(f'<span class="cpm-val">£{r.bid_cpm_gbp:.2f} CPM</span>')
            if r.spend_gbp:
                meta_parts.append(f'<span class="spend-val">£{r.spend_gbp:.2f}</span>')
            meta_parts.append(f'<span style="color:#3a3d4a;">{r.context.estimated_impressions:,} impr</span>')

            # Score breakdown pills
            score_pills_html = ""
            if r.score and r.decision != "skipped":
                score_pills_html = (
                    f'<div class="esc-scores">'
                    f'<span class="esc-score-pill">Relevance {int(r.score.brand_relevance)}</span>'
                    f'<span class="esc-score-pill">Risk {int(r.score.safety_risk)}</span>'
                    f'<span class="esc-score-pill">Intent {int(r.score.intent_strength)}</span>'
                    f'</div>'
                )

            reasoning_html = ""
            if r.score and r.score.reasoning:
                reasoning_html = f'<div class="bid-reasoning">{r.score.reasoning}</div>'

            creative_html = ""
            if r.creative:
                creative_html = (
                    f'<div style="margin-top:8px; padding:8px 12px; background:#10b98108; '
                    f'border-radius:6px; border:1px solid #10b98118;">'
                    f'<div style="font-family:JetBrains Mono,monospace; font-size:0.65rem; '
                    f'color:#10b981; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;">'
                    f'Generated Creative</div>'
                    f'<div style="color:#c8cad4; font-size:0.82rem; font-weight:600;">{r.creative.headline}</div>'
                    f'<div style="color:#8b8fa3; font-size:0.78rem; margin-top:2px;">{r.creative.body}</div>'
                    f'<div style="color:#60a5fa; font-size:0.75rem; margin-top:4px;">{r.creative.cta}</div>'
                    f'</div>'
                )

            human_badge = ""
            if r.human_approved is True:
                human_badge = (
                    ' <span style="font-family:JetBrains Mono,monospace; font-size:0.6rem; '
                    'background:#3b82f615; color:#60a5fa; padding:2px 6px; border-radius:3px; '
                    'margin-left:6px;">HUMAN APPROVED</span>'
                )

            st.markdown(
                f'<div class="bid-card bid-card--{css}">'
                f'<div class="bid-decision bid-decision--{css}">{label}</div>{human_badge}'
                f'<span class="bid-channel">{r.context.channel} · {r.context.topic_category}</span>'
                f'<div class="bid-prompt">"{r.context.user_prompt[:120]}"</div>'
                f'{score_pills_html}'
                f'<div class="bid-meta">{"".join(f"<span>{p}</span>" for p in meta_parts)}</div>'
                f'{reasoning_html}'
                f'{creative_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Right column: Escalation Queue + Supervision ─────────────────────────────
with col_right:
    st.markdown('<div class="section-label">⚠️ Escalation Queue</div>', unsafe_allow_html=True)

    if not st.session_state.escalation_queue:
        st.markdown(
            '<div style="color:#3a3d4a; font-size:0.82rem; padding:20px 0; text-align:center;">'
            'No items pending review'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for idx, r in enumerate(st.session_state.escalation_queue):
            st.markdown(
                f'<div class="esc-card">'
                f'<span class="bid-channel">{r.context.channel} · {r.context.topic_category}</span>'
                f'<div class="bid-prompt">"{r.context.user_prompt[:100]}"</div>',
                unsafe_allow_html=True,
            )
            if r.score:
                st.markdown(
                    f'<div class="esc-scores">'
                    f'<span class="esc-score-pill">Overall {int(r.score.overall_score)}</span>'
                    f'<span class="esc-score-pill">Relevance {int(r.score.brand_relevance)}</span>'
                    f'<span class="esc-score-pill">Risk {int(r.score.safety_risk)}</span>'
                    f'<span class="esc-score-pill">Intent {int(r.score.intent_strength)}</span>'
                    f'</div>'
                    f'<div class="bid-reasoning">{r.score.reasoning}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            if c1.button("✅ Approve", key=f"approve_{idx}", use_container_width=True):
                approved_result = agent.process_escalation(
                    r, True, st.session_state.brief, st.session_state.state
                )
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

    # ── Supervision Events ────────────────────────────────────────────────────
    if agent_state.supervision_events:
        st.markdown("---")
        st.markdown('<div class="section-label">🛡️ Overmind Alerts</div>', unsafe_allow_html=True)
        for event in reversed(agent_state.supervision_events):
            sev_class = "critical" if event.severity == "critical" else "warning"
            st.markdown(
                f'<div class="sup-event sup-event--{sev_class}">'
                f'<div class="sup-event-label sup-event-label--{sev_class}">'
                f'{"🚨" if sev_class == "critical" else "⚠️"} {event.rule_violated.replace("_", " ")}'
                f'</div>'
                f'<div class="sup-event-desc">{event.description}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ── Summary Report ────────────────────────────────────────────────────────────
if st.session_state.stream_complete and results:
    st.markdown("---")
    pending = len(st.session_state.escalation_queue)
    budget_saved = daily_budget - total_spend
    blocked_spend = sum(
        (r.bid_cpm_gbp or 0) * r.context.estimated_impressions / 1000
        for r in results if r.decision == "blocked"
    )

    summary_parts = [
        f"Evaluated **{all_evaluated}** placements across {len(set(r.context.channel for r in results))} channels.",
        f"Auto-bid on **{len(auto_bids)}**, escalated **{len(escalated_items) + pending}**, skipped **{len(skipped_items)}**, blocked **{len(blocked_items)}**.",
        f"Total spend: **£{total_spend:.2f}** of £{daily_budget:.0f} budget ({budget_pct*100:.0f}% utilized).",
    ]
    if blocked_spend > 0:
        summary_parts.append(f"Overmind prevented **£{blocked_spend:.2f}** in risky spend.")
    if budget_saved > 0:
        summary_parts.append(f"Budget saved by skipping low-fit contexts: **£{budget_saved:.2f}**.")
    if pending > 0:
        summary_parts.append(f"**{pending}** placements awaiting human review in the escalation queue.")

    st.markdown(
        '<div class="section-label">📋 Summary Report</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="background:#0d0f16; border:1px solid #1a1d28; border-radius:10px; padding:16px 20px;">'
        + "<br/>".join(summary_parts)
        + '</div>',
        unsafe_allow_html=True,
    )

# ── Run the bid stream ────────────────────────────────────────────────────────
if start_stream:
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
            import traceback; traceback.print_exc()
            market_context = ""

    # Step 2: Generate dynamic contexts for this brand
    with st.spinner("📡 Generating ad opportunities for this brand..."):
        try:
            raw_contexts = generate_contexts(brief, agent.ask_claude)
        except Exception as e:
            import traceback; traceback.print_exc()
            raw_contexts = []

    if not raw_contexts:
        st.error("Failed to generate contexts. Check your API key.")
        st.session_state.stream_running = False
        st.stop()

    contexts = [ConversationContext(**c) for c in raw_contexts]
    progress_bar = st.progress(0, text="Initializing bid stream...")

    for i, ctx in enumerate(contexts):
        if st.session_state.state.status == "paused":
            break

        progress_bar.progress(
            (i + 1) / len(contexts),
            text=f"Evaluating {i+1}/{len(contexts)} · {ctx.topic_category}",
        )

        try:
            result = agent.process_context(
                ctx, brief, st.session_state.state, market_context
            )
        except Exception as e:
            import traceback; traceback.print_exc()
            continue

        if result.decision == "escalated":
            st.session_state.escalation_queue.append(result)
        else:
            st.session_state.results.append(result)

    st.session_state.stream_running = False
    st.session_state.stream_complete = True
    progress_bar.empty()
    st.rerun()
