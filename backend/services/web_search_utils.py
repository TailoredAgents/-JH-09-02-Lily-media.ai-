"""
Shared utilities for parsing OpenAI web search responses.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
import logging

logger = logging.getLogger(__name__)

def parse_openai_web_search_results(response: Any, query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Normalize OpenAI Responses API result into a list of {title,url,snippet,date} dicts.
    
    Args:
        response: OpenAI response object
        query: The search query for context
        max_results: Maximum number of results to return
        
    Returns:
        List of normalized search result dictionaries
    """
    results: List[Dict[str, str]] = []
    
    # Tool calls branch - parse structured web search results
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            if getattr(tool_call, "type", None) == "web_search":
                ws = getattr(tool_call, "web_search", None)
                if ws and hasattr(ws, "results"):
                    for item in list(ws.results)[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                            "date": item.get("date", datetime.now().strftime('%Y-%m-%d'))
                        })
    
    # Fallback: parse output_text for JSON or links
    if not results:
        content = getattr(response, "output_text", None) or str(response)
        
        # Try to parse JSON first
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed[:max_results]  # assume correct shape
            if isinstance(parsed, dict) and "results" in parsed:
                return list(parsed["results"])[:max_results]
        except Exception:
            pass
        
        # Look for URLs in the content
        urls = re.findall(r"(https?://\S+)", content)
        if urls:
            for i, url in enumerate(urls[:max_results]):
                results.append({
                    "title": f"Search result {i+1} for: {query}",
                    "url": url,
                    "snippet": content[:200] + ("..." if len(content) > 200 else ""),
                    "date": datetime.now().strftime('%Y-%m-%d')
                })
        else:
            # Create single fallback result
            results.append({
                "title": f"Web search results for: {query}",
                "url": f"https://search.example.com/results?q={query.replace(' ', '+')}",
                "snippet": content[:300] + ("..." if len(content) > 300 else ""),
                "date": datetime.now().strftime('%Y-%m-%d')
            })
    
    return results[:max_results]

def as_web_results(dicts: List[Dict[str, str]]):
    """
    Optional helper for services that use a WebSearchResult dataclass.
    """
    # Avoid circular import at module import time
    from .web_research_service import WebSearchResult
    
    out = []
    for d in dicts:
        out.append(WebSearchResult(
            title=d.get("title", ""),
            url=d.get("url", ""),
            snippet=d.get("snippet", ""),
            date=d.get("date", datetime.now().strftime('%Y-%m-%d')),
            source="gpt_5_web_search"
        ))
    return out