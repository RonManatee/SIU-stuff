"""
Social profile discovery.

IMPORTANT: this module does NOT scrape Google/Bing/social platform search
results pages directly. Automating scraping of search engine result pages
violates their Terms of Service, is fragile (constant blocking/CAPTCHAs),
and is a legal liability for an insurer to have in a production tool.

Instead it issues "site:<platform> <query>" style search-operator queries
through an official, licensed search API:
  - Bing Web Search API (BING_SEARCH_API_KEY)
  - SerpAPI, which is a licensed wrapper around Google (SERPAPI_API_KEY)

If neither key is configured, the module runs in MOCK MODE and returns
clearly-labeled placeholder results so the rest of the pipeline can be
developed/tested without live credentials or network calls.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import config
from modules.audit_log import log_query

BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def _mock_result(platform: str, query: str) -> dict:
    return {
        "platform": platform,
        "query": query,
        "mock": True,
        "results": [
            {
                "title": f"[MOCK] Possible {platform} profile match",
                "url": f"https://{platform}/example-profile",
                "snippet": "No live search API key configured (BING_SEARCH_API_KEY / "
                           "SERPAPI_API_KEY) -- this is a placeholder, not a real result.",
            }
        ],
    }


def _search_bing(platform: str, query: str) -> dict:
    headers = {"Ocp-Apim-Subscription-Key": config.BING_SEARCH_API_KEY}
    params = {"q": f'site:{platform} "{query}"', "count": 5}
    resp = requests.get(BING_ENDPOINT, headers=headers, params=params,
                         timeout=config.REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("webPages", {}).get("value", [])
    return {
        "platform": platform,
        "query": query,
        "mock": False,
        "results": [
            {"title": h.get("name"), "url": h.get("url"), "snippet": h.get("snippet")}
            for h in hits
        ],
    }


def _search_serpapi(platform: str, query: str) -> dict:
    params = {
        "engine": "google",
        "q": f'site:{platform} "{query}"',
        "api_key": config.SERPAPI_API_KEY,
        "num": 5,
    }
    resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    hits = data.get("organic_results", [])
    return {
        "platform": platform,
        "query": query,
        "mock": False,
        "results": [
            {"title": h.get("title"), "url": h.get("link"), "snippet": h.get("snippet")}
            for h in hits
        ],
    }


def _search_one_platform(platform: str, query: str) -> dict:
    try:
        if config.BING_SEARCH_API_KEY:
            result = _search_bing(platform, query)
            source = "bing_web_search_api"
        elif config.SERPAPI_API_KEY:
            result = _search_serpapi(platform, query)
            source = "serpapi"
        else:
            result = _mock_result(platform, query)
            source = "mock"
    except requests.RequestException as e:
        result = {"platform": platform, "query": query, "mock": False, "error": str(e), "results": []}
        source = "error"

    log_query(
        module="social_search",
        query=query,
        source=f"{source}:{platform}",
        result_summary=f"{len(result.get('results', []))} hit(s)",
        mock=result.get("mock", False),
    )
    time.sleep(config.REQUEST_DELAY_SECONDS)
    return result


def search_social_profiles(name_or_username: str, platforms=None) -> list:
    """
    Run site-restricted search-operator queries across platforms concurrently.
    Returns a list of per-platform result dicts.
    """
    platforms = platforms or config.SOCIAL_PLATFORMS
    results = []
    with ThreadPoolExecutor(max_workers=min(8, len(platforms))) as executor:
        futures = {
            executor.submit(_search_one_platform, platform, name_or_username): platform
            for platform in platforms
        }
        for future in as_completed(futures):
            results.append(future.result())
    return results
