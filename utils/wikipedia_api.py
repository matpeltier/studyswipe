import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_ACTION_API = "https://en.wikipedia.org/w/api.php"

_session = requests.Session()
_session.headers.update({"User-Agent": "StudySwipe/1.0 (educational project)"})


def get_summary(title: str) -> Optional[dict]:
    try:
        resp = _session.get(
            f"{WIKIPEDIA_API}/page/summary/{title}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "title": data.get("title", title),
            "extract": data.get("extract", ""),
            "thumbnail": data.get("thumbnail", {}).get("source"),
            "original_image": data.get("originalimage", {}).get("source"),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
    except Exception as e:
        logger.warning("Failed to fetch summary for %s: %s", title, e)
        return None


def get_extract(title: str, sentences: int = 5) -> Optional[str]:
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "exsentences": sentences,
            "exintro": True,
            "explaintext": True,
            "format": "json",
        }
        resp = _session.get(WIKIPEDIA_ACTION_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            return page.get("extract", "")
    except Exception as e:
        logger.warning("Failed to fetch extract for %s: %s", title, e)
    return None


def search_articles(query: str, limit: int = 10) -> list[dict]:
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
        }
        resp = _session.get(WIKIPEDIA_ACTION_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("query", {}).get("search", []):
            results.append(
                {
                    "title": item["title"],
                    "snippet": item.get("snippet", ""),
                    "pageid": item.get("pageid"),
                }
            )
        return results
    except Exception as e:
        logger.warning("Failed to search for %s: %s", query, e)
        return []


def get_random_articles(count: int = 10) -> list[str]:
    try:
        params = {
            "action": "query",
            "list": "random",
            "rnnamespace": 0,
            "rnlimit": count,
            "format": "json",
        }
        resp = _session.get(WIKIPEDIA_ACTION_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [item["title"] for item in data.get("query", {}).get("random", [])]
    except Exception as e:
        logger.warning("Failed to get random articles: %s", e)
        return []


def get_page_views(article: str, days: int = 30) -> Optional[dict]:
    try:
        from datetime import datetime, timedelta

        end = datetime.utcnow().strftime("%Y%m%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}"
        resp = _session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        total_views = sum(item.get("views", 0) for item in items)
        seven_day = (
            sum(item.get("views", 0) for item in items[:7])
            if len(items) >= 7
            else total_views
        )
        return {
            "pageviews_30d": total_views,
            "pageviews_7d": seven_day,
            "daily_data": [
                (item.get("timestamp", ""), item.get("views", 0)) for item in items
            ],
        }
    except Exception as e:
        logger.warning("Failed to get page views for %s: %s", article, e)
        return None
