import hashlib
from urllib.parse import urlparse
from ..config import SEARCH_CACHE_TTL
from ..db import cache_get, cache_set

DENYLIST = {
    "facebook.com", "instagram.com", "linkedin.com", "google.com", "maps.google.com",
    "healthengine.com.au", "hotdoc.com.au", "whitecoat.com.au", "healthdirect.gov.au",
}
def search_web(query: str) -> list[dict[str, str]]:
    key = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    cached = cache_get(f"search:{key}")
    if cached is not None:
        return cached

    try:
        from ddgs import DDGS
        results = list(DDGS().text(query, max_results=5))
    except Exception as exc:
        raise RuntimeError("Website search is temporarily unavailable; paste a URL manually.") from exc
    if not results:
        raise RuntimeError("No website results were found; paste a URL manually.")

    clean = []
    for item in results:
        url = str(item.get("href") or item.get("url") or "")
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if url and not any(host == domain or host.endswith(f".{domain}") for domain in DENYLIST):
            clean.append({"url": url, "title": str(item.get("title", "")), "snippet": str(item.get("body", ""))})
    cache_set(f"search:{key}", clean, SEARCH_CACHE_TTL)
    return clean
