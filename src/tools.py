"""
Tavily search tools + any external integrations.
"""
import os
from tavily import TavilyClient


def get_tavily_client() -> TavilyClient:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set in .env")
    return TavilyClient(api_key=api_key)


def research_market_context(query: str) -> str:
    """
    Research market/competitive context for a campaign.
    Returns a formatted string ready to inject into an agent prompt.
    """
    client = get_tavily_client()
    # get_search_context returns pre-chunked, RAG-ready string — no processing needed
    context = client.get_search_context(
        query=query,
        search_depth="basic",
        max_results=5,
    )
    return context


def search_audience_signals(audience_description: str) -> str:
    """
    Search for real-time audience intent signals and content preferences.
    """
    client = get_tavily_client()
    results = client.search(
        query=f"audience behavior trends {audience_description} 2025",
        search_depth="basic",
        topic="news",
        max_results=3,
    )
    snippets = [r.get("content", "") for r in results.get("results", [])]
    return "\n\n".join(snippets)


def search_competitive_ads(brand_category: str) -> str:
    """
    Research competitor ad strategies in a category.
    """
    client = get_tavily_client()
    answer = client.qna_search(
        query=f"best performing ad strategies for {brand_category} in 2025 UK market"
    )
    return answer
