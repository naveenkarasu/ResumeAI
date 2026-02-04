"""Web search using DuckDuckGo (FREE, no API key required)"""

from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS

import sys
sys.path.append(str(__file__).rsplit("src", 1)[0])
from config.settings import settings


class WebSearch:
    """
    Web search using DuckDuckGo.

    FREE - No API key required.
    Uses duckduckgo-search library.
    """

    def __init__(self, max_results: Optional[int] = None):
        self.max_results = max_results or settings.web_search_max_results
        self.enabled = settings.web_search_enabled

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        region: str = "wt-wt",  # Worldwide
        time_range: Optional[str] = None  # d=day, w=week, m=month, y=year
    ) -> List[Dict[str, Any]]:
        """
        Search the web using DuckDuckGo.

        Args:
            query: Search query
            max_results: Maximum number of results
            region: Region code (wt-wt = worldwide)
            time_range: Time filter (d, w, m, y)

        Returns:
            List of search results with title, link, and snippet
        """
        if not self.enabled:
            return []

        max_results = max_results or self.max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    query,
                    region=region,
                    timelimit=time_range,
                    max_results=max_results
                ))

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", ""))
                }
                for r in results
            ]

        except Exception as e:
            print(f"Web search error: {e}")
            return []

    def search_news(
        self,
        query: str,
        max_results: Optional[int] = None,
        time_range: str = "w"  # Default to past week
    ) -> List[Dict[str, Any]]:
        """Search for news articles"""
        if not self.enabled:
            return []

        max_results = max_results or self.max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(
                    query,
                    timelimit=time_range,
                    max_results=max_results
                ))

            return [
                {
                    "title": r.get("title", ""),
                    "link": r.get("url", r.get("link", "")),
                    "snippet": r.get("body", ""),
                    "date": r.get("date", ""),
                    "source": r.get("source", "")
                }
                for r in results
            ]

        except Exception as e:
            print(f"News search error: {e}")
            return []

    def search_company(self, company_name: str) -> Dict[str, Any]:
        """Search for company information"""
        results = self.search(f"{company_name} company about careers")

        return {
            "company": company_name,
            "results": results,
            "query": f"{company_name} company about careers"
        }

    def search_job_market(self, job_title: str, location: Optional[str] = None) -> Dict[str, Any]:
        """Search for job market information"""
        query = f"{job_title} salary job market trends 2024"
        if location:
            query += f" {location}"

        results = self.search(query)

        return {
            "job_title": job_title,
            "location": location,
            "results": results
        }

    def format_results_for_context(self, results: List[Dict[str, Any]]) -> str:
        """Format search results as context for LLM"""
        if not results:
            return "No web search results found."

        formatted = ["Web Search Results:"]

        for i, r in enumerate(results, 1):
            formatted.append(f"\n{i}. {r['title']}")
            formatted.append(f"   {r['snippet']}")
            formatted.append(f"   Source: {r['link']}")

        return "\n".join(formatted)
