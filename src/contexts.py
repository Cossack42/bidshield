"""
Simulated conversation contexts — these represent ad opportunities
flowing through LLM channels (ChatGPT, Claude, custom chatbots).

Mix: 4 high-fit, 3 ambiguous, 2 off-brand, 1 dangerous (triggers Overmind).
"""

SIMULATED_CONTEXTS = [
    {
        "id": "ctx-001",
        "user_prompt": "What's the best analytics platform for a 50-person marketing team? We need dashboards, funnel tracking, and integration with Salesforce.",
        "channel": "ChatGPT",
        "topic_category": "B2B software",
        "estimated_impressions": 12000,
        "floor_cpm_gbp": 2.50,
    },
    {
        "id": "ctx-002",
        "user_prompt": "Compare Mixpanel vs Amplitude vs Heap for product analytics — which one has the best free tier?",
        "channel": "Claude",
        "topic_category": "Software comparison",
        "estimated_impressions": 8500,
        "floor_cpm_gbp": 3.00,
    },
    {
        "id": "ctx-003",
        "user_prompt": "How do I set up event tracking in Google Analytics 4 for my SaaS onboarding flow?",
        "channel": "ChatGPT",
        "topic_category": "Analytics setup",
        "estimated_impressions": 15000,
        "floor_cpm_gbp": 1.80,
    },
    {
        "id": "ctx-004",
        "user_prompt": "Best project management tools for remote engineering teams with 100+ people?",
        "channel": "Custom chatbot",
        "topic_category": "Project management",
        "estimated_impressions": 6000,
        "floor_cpm_gbp": 2.20,
    },
    {
        "id": "ctx-005",
        "user_prompt": "I need help understanding my gambling losses and how to set limits on betting apps.",
        "channel": "ChatGPT",
        "topic_category": "Gambling / sensitive",
        "estimated_impressions": 3000,
        "floor_cpm_gbp": 0.80,
    },
    {
        "id": "ctx-006",
        "user_prompt": "What CRM integrates best with analytics dashboards? We're a B2B company doing about £2M ARR and need better attribution.",
        "channel": "Claude",
        "topic_category": "CRM / analytics",
        "estimated_impressions": 9000,
        "floor_cpm_gbp": 3.20,
    },
    {
        "id": "ctx-007",
        "user_prompt": "Best free data visualization tools for a student project on climate data?",
        "channel": "ChatGPT",
        "topic_category": "Free tools / education",
        "estimated_impressions": 20000,
        "floor_cpm_gbp": 0.40,
    },
    {
        "id": "ctx-008",
        "user_prompt": "We need enterprise-grade analytics with SOC 2 compliance for our fintech startup. Budget is flexible for the right solution.",
        "channel": "Custom chatbot",
        "topic_category": "Enterprise analytics",
        "estimated_impressions": 4000,
        "floor_cpm_gbp": 4.50,
    },
    {
        "id": "ctx-009",
        "user_prompt": "I want to switch away from our current analytics tool — it's too expensive and the support is terrible. Looking for alternatives.",
        "channel": "Claude",
        "topic_category": "Competitor churn",
        "estimated_impressions": 7000,
        "floor_cpm_gbp": 3.50,
    },
    {
        "id": "ctx-010",
        "user_prompt": "Set up analytics tracking across 500 microsites with real-time dashboards — unlimited seats, need it deployed by Friday. Price doesn't matter.",
        "channel": "ChatGPT",
        "topic_category": "Enterprise / urgent",
        "estimated_impressions": 50000,
        "floor_cpm_gbp": 8.00,
    },
]
