import logging
import time

import requests

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_ACTION_API = "https://en.wikipedia.org/w/api.php"

_session = requests.Session()
_session.headers.update({"User-Agent": "StudySwipe/1.0 (educational project)"})


def get_summary(title):
    retries = 0
    while retries < 3:
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
            retries = retries + 1
            logger.warning("Failed to fetch summary for %s (attempt %d): %s", title, retries, e)
            if retries < 3:
                time.sleep(1)
    return None


def get_extract(title, sentences=5):
    retries = 0
    while retries < 3:
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
            return None
        except Exception as e:
            retries = retries + 1
            logger.warning("Failed to fetch extract for %s (attempt %d): %s", title, retries, e)
            if retries < 3:
                time.sleep(1)
    return None


def search_articles(query, limit=10):
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


def get_random_articles(count=10):
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
        titles = []
        for item in data.get("query", {}).get("random", []):
            titles.append(item["title"])
        return titles
    except Exception as e:
        logger.warning("Failed to get random articles: %s", e)
        return []


def get_page_views(article, days=30):
    try:
        from datetime import datetime, timedelta

        end = datetime.utcnow().strftime("%Y%m%d")
        start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y%m%d")
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        total_views = 0
        for item in items:
            total_views = total_views + item.get("views", 0)
        seven_day = 0
        if len(items) >= 7:
            for item in items[:7]:
                seven_day = seven_day + item.get("views", 0)
        else:
            seven_day = total_views
        return {
            "pageviews_30d": total_views,
            "pageviews_7d": seven_day,
        }
    except Exception as e:
        logger.warning("Failed to get page views for %s: %s", article, e)
        return None
