import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATAB_SPARQL = "https://query.wikidata.org/sparql"

_session = requests.Session()
_session.headers.update({"User-Agent": "StudySwipe/1.0 (educational project)"})


def search_entity(query: str, limit: int = 5) -> list[dict]:
    try:
        params = {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": limit,
            "format": "json",
        }
        resp = _session.get(WIKIDATA_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("search", []):
            results.append(
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "description": item.get("description", ""),
                }
            )
        return results
    except Exception as e:
        logger.warning("Wikidata search failed for %s: %s", query, e)
        return []


def get_entity(id: str) -> Optional[dict]:
    try:
        params = {
            "action": "wbgetentities",
            "ids": id,
            "props": "labels|descriptions|claims",
            "languages": "en",
            "format": "json",
        }
        resp = _session.get(WIKIDATA_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        entity = data.get("entities", {}).get(id, {})
        label = entity.get("labels", {}).get("en", {}).get("value", "")
        description = entity.get("descriptions", {}).get("en", {}).get("value", "")
        return {
            "id": id,
            "label": label,
            "description": description,
        }
    except Exception as e:
        logger.warning("Wikidata entity fetch failed for %s: %s", id, e)
        return None


def get_trending_topics(limit: int = 20) -> list[dict]:
    try:
        query = (
            """
        SELECT ?item ?itemLabel ?itemDescription ?article WHERE {
            ?article schema:about ?item ;
                     schema:isPartOf <https://en.wikipedia.org/> .
            SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        LIMIT %d
        """
            % limit
        )
        resp = _session.get(
            WIKIDATAB_SPARQL,
            params={"query": query, "format": "json"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for binding in data.get("results", {}).get("bindings", []):
            results.append(
                {
                    "wikidata_id": binding.get("item", {})
                    .get("value", "")
                    .split("/")[-1],
                    "label": binding.get("itemLabel", {}).get("value", ""),
                    "description": binding.get("itemDescription", {}).get("value", ""),
                    "article_url": binding.get("article", {}).get("value", ""),
                }
            )
        return results
    except Exception as e:
        logger.warning("Wikidata trending fetch failed: %s", e)
        return []
