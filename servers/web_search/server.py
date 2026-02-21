"""Web Search MCP server powered by Tavily API.

Provides structured web search, news search, site-scoped search,
content extraction, website crawling, and URL mapping tools
for agentic workflows.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP(name="Web Search Server")

TAVILY_BASE_URL = "https://api.tavily.com"


def _get_api_key() -> str:
    key = os.environ.get("TAVILY_API_KEY", "")
    if not key:
        raise ValueError("TAVILY_API_KEY environment variable is required")
    return key


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }


async def _tavily_post(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Make a POST request to Tavily API and return JSON response."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{TAVILY_BASE_URL}/{endpoint}",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def _format_search_results(data: dict[str, Any]) -> dict[str, Any]:
    """Format Tavily search response into structured output."""
    results = []
    for r in data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "score": round(r.get("score", 0.0), 4),
            "published_date": r.get("published_date"),
        })
    output: dict[str, Any] = {
        "query": data.get("query", ""),
        "results": results,
        "result_count": len(results),
    }
    if data.get("answer"):
        output["answer"] = data["answer"]
    if data.get("images"):
        output["images"] = data["images"]
    if data.get("response_time"):
        output["response_time_seconds"] = round(data["response_time"], 3)
    return output


# ── Search Tools ─────────────────────────────────────────────────


@mcp.tool()
async def search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
    topic: str = "general",
    time_range: str | None = None,
    country: str | None = None,
) -> dict[str, Any]:
    """Search the web and return structured results with optional AI-generated answer.

    Args:
        query: The search query to execute.
        max_results: Number of results to return (1-20, default 5).
        search_depth: "basic" (fast, 1 credit), "advanced" (thorough, 2 credits),
                      "fast" (low latency), or "ultra-fast" (minimal latency).
        include_answer: If True, includes an AI-synthesized answer from the results.
        topic: "general" for web search, "news" for news-focused results.
        time_range: Filter by recency: "day", "week", "month", or "year". None for all time.
        country: Boost results from a specific country (e.g. "us", "gb", "de").
                 Only works when topic is "general".
    """
    payload: dict[str, Any] = {
        "query": query,
        "max_results": min(max(max_results, 1), 20),
        "search_depth": search_depth,
        "include_answer": include_answer,
        "topic": topic,
    }
    if time_range:
        payload["time_range"] = time_range
    if country and topic == "general":
        payload["country"] = country

    data = await _tavily_post("search", payload)
    return _format_search_results(data)


@mcp.tool()
async def search_news(
    query: str,
    max_results: int = 5,
    time_range: str = "week",
    include_answer: bool = True,
    country: str | None = None,
) -> dict[str, Any]:
    """Search recent news articles. Optimized for current events and breaking news.

    Args:
        query: The news search query.
        max_results: Number of results to return (1-20, default 5).
        time_range: Recency filter: "day", "week" (default), "month", or "year".
        include_answer: If True, includes an AI-synthesized answer summary.
        country: Boost results from a specific country (e.g. "us", "gb").
    """
    payload: dict[str, Any] = {
        "query": query,
        "max_results": min(max(max_results, 1), 20),
        "search_depth": "basic",
        "include_answer": include_answer,
        "topic": "news",
        "time_range": time_range,
    }
    if country:
        payload["country"] = country

    data = await _tavily_post("search", payload)
    return _format_search_results(data)


@mcp.tool()
async def search_site(
    query: str,
    domain: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = False,
) -> dict[str, Any]:
    """Search within a specific website/domain only.

    Useful for finding content on documentation sites, wikis, or specific platforms.

    Args:
        query: The search query.
        domain: Domain to restrict search to (e.g. "docs.python.org", "github.com").
        max_results: Number of results (1-20, default 5).
        search_depth: "basic" or "advanced" for deeper relevance matching.
        include_answer: If True, includes an AI-synthesized answer.
    """
    payload: dict[str, Any] = {
        "query": query,
        "max_results": min(max(max_results, 1), 20),
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_domains": [domain.strip()],
    }

    data = await _tavily_post("search", payload)
    return _format_search_results(data)


@mcp.tool()
async def search_sites(
    query: str,
    domains: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = False,
) -> dict[str, Any]:
    """Search across multiple specific websites/domains.

    Useful for comparing information across trusted sources or restricting
    results to a curated set of domains.

    Args:
        query: The search query.
        domains: Comma-separated list of domains (e.g. "python.org,docs.python.org,pypi.org").
        max_results: Number of results (1-20, default 5).
        search_depth: "basic" or "advanced" for deeper relevance matching.
        include_answer: If True, includes an AI-synthesized answer.
    """
    domain_list = [d.strip() for d in domains.split(",") if d.strip()]
    if not domain_list:
        raise ValueError("At least one domain is required")

    payload: dict[str, Any] = {
        "query": query,
        "max_results": min(max(max_results, 1), 20),
        "search_depth": search_depth,
        "include_answer": include_answer,
        "include_domains": domain_list,
    }

    data = await _tavily_post("search", payload)
    return _format_search_results(data)


@mcp.tool()
async def search_exclude(
    query: str,
    exclude_domains: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> dict[str, Any]:
    """Search the web while excluding specific domains from results.

    Useful for filtering out noisy or low-quality sources.

    Args:
        query: The search query.
        exclude_domains: Comma-separated domains to exclude (e.g. "reddit.com,quora.com").
        max_results: Number of results (1-20, default 5).
        search_depth: "basic" or "advanced".
        include_answer: If True, includes an AI-synthesized answer.
    """
    domain_list = [d.strip() for d in exclude_domains.split(",") if d.strip()]

    payload: dict[str, Any] = {
        "query": query,
        "max_results": min(max(max_results, 1), 20),
        "search_depth": search_depth,
        "include_answer": include_answer,
        "exclude_domains": domain_list,
    }

    data = await _tavily_post("search", payload)
    return _format_search_results(data)


# ── Content Extraction Tools ────────────────────────────────────


@mcp.tool()
async def extract(
    urls: str,
    format: str = "markdown",
    extract_depth: str = "basic",
) -> dict[str, Any]:
    """Extract clean content from one or more web pages.

    Returns the full page content in markdown or plain text format.
    Useful for reading articles, documentation, or any web page content.

    Args:
        urls: Single URL or comma-separated list of URLs to extract (max 20).
        format: Output format: "markdown" (default) or "text".
        extract_depth: "basic" (fast) or "advanced" (handles tables, embedded content, protected sites).
    """
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        raise ValueError("At least one URL is required")
    if len(url_list) > 20:
        raise ValueError("Maximum 20 URLs per request")

    payload: dict[str, Any] = {
        "urls": url_list,
        "format": format,
        "extract_depth": extract_depth,
    }

    data = await _tavily_post("extract", payload)

    results = []
    for r in data.get("results", []):
        content = r.get("raw_content", "")
        results.append({
            "url": r.get("url", ""),
            "content": content,
            "content_length": len(content),
        })

    failed = []
    for f in data.get("failed_results", []):
        failed.append({
            "url": f.get("url", ""),
            "error": f.get("error", "Unknown error"),
        })

    output: dict[str, Any] = {
        "results": results,
        "success_count": len(results),
        "failed_count": len(failed),
    }
    if failed:
        output["failed"] = failed
    if data.get("response_time"):
        output["response_time_seconds"] = round(data["response_time"], 3)
    return output


# ── Crawl & Map Tools ───────────────────────────────────────────


@mcp.tool()
async def crawl(
    url: str,
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    instructions: str | None = None,
    select_paths: str | None = None,
    exclude_paths: str | None = None,
    format: str = "markdown",
) -> dict[str, Any]:
    """Crawl a website starting from a URL, following links to discover and extract content.

    Returns structured content from all discovered pages. Useful for indexing
    documentation sites, knowledge bases, or gathering comprehensive site content.

    Args:
        url: The root URL to begin crawling.
        max_depth: How many levels deep to follow links (1-5, default 1).
        max_breadth: Max links to follow per page level (1-500, default 20).
        limit: Total pages to process before stopping (default 50).
        instructions: Natural language instructions to guide the crawler
                      (e.g. "focus on API documentation pages"). Doubles credit cost.
        select_paths: Comma-separated regex patterns for URL paths to include
                      (e.g. "/docs/.*,/api/.*").
        exclude_paths: Comma-separated regex patterns for URL paths to exclude
                       (e.g. "/blog/.*,/changelog/.*").
        format: Output format: "markdown" (default) or "text".
    """
    payload: dict[str, Any] = {
        "url": url,
        "max_depth": min(max(max_depth, 1), 5),
        "max_breadth": min(max(max_breadth, 1), 500),
        "limit": max(limit, 1),
        "format": format,
    }
    if instructions:
        payload["instructions"] = instructions
    if select_paths:
        payload["select_paths"] = [p.strip() for p in select_paths.split(",") if p.strip()]
    if exclude_paths:
        payload["exclude_paths"] = [p.strip() for p in exclude_paths.split(",") if p.strip()]

    data = await _tavily_post("crawl", payload)

    results = []
    for r in data.get("results", []):
        content = r.get("raw_content", "")
        results.append({
            "url": r.get("url", ""),
            "content": content,
            "content_length": len(content),
        })

    output: dict[str, Any] = {
        "base_url": data.get("base_url", url),
        "results": results,
        "pages_crawled": len(results),
    }
    if data.get("response_time"):
        output["response_time_seconds"] = round(data["response_time"], 3)
    return output


@mcp.tool()
async def map_urls(
    url: str,
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    instructions: str | None = None,
    select_paths: str | None = None,
    exclude_paths: str | None = None,
) -> dict[str, Any]:
    """Discover and map all URLs on a website without extracting content.

    Returns a flat list of discovered URLs. Useful for planning what pages to
    extract, understanding site structure, or building sitemaps.
    Much faster and cheaper than crawl since it only discovers URLs.

    Args:
        url: The root URL to begin mapping.
        max_depth: How many levels deep to follow links (1-5, default 1).
        max_breadth: Max links to follow per page level (1-500, default 20).
        limit: Total links to process before stopping (default 50).
        instructions: Natural language instructions to guide the mapper
                      (e.g. "find all product pages"). Doubles credit cost.
        select_paths: Comma-separated regex patterns for URL paths to include.
        exclude_paths: Comma-separated regex patterns for URL paths to exclude.
    """
    payload: dict[str, Any] = {
        "url": url,
        "max_depth": min(max(max_depth, 1), 5),
        "max_breadth": min(max(max_breadth, 1), 500),
        "limit": max(limit, 1),
    }
    if instructions:
        payload["instructions"] = instructions
    if select_paths:
        payload["select_paths"] = [p.strip() for p in select_paths.split(",") if p.strip()]
    if exclude_paths:
        payload["exclude_paths"] = [p.strip() for p in exclude_paths.split(",") if p.strip()]

    data = await _tavily_post("map", payload)

    urls_found = data.get("results", [])
    return {
        "base_url": data.get("base_url", url),
        "urls": urls_found,
        "url_count": len(urls_found),
        "response_time_seconds": round(data.get("response_time", 0), 3),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.http_app(stateless_http=True),
        host="0.0.0.0",
        port=9001,
    )
