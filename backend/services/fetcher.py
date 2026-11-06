import ipaddress
import urllib.robotparser
import socket
import hashlib
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..config import USER_AGENT
from ..config import FETCH_CACHE_TTL
from ..db import cache_get, cache_set


def _public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS website URLs are allowed.")
    addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError("Private or internal website addresses are blocked.")


def fetch_page(url: str) -> str:
    cache_key = f"fetch:{hashlib.sha256(url.strip().lower().encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return str(cached)
    current_url = url
    with httpx.Client(timeout=15, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(5):
            _public_host(current_url)
            parsed = urlparse(current_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            robots = client.get(robots_url)
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            if robots.status_code < 400:
                parser.parse(robots.text.splitlines())
                if not parser.can_fetch(USER_AGENT, current_url):
                    raise PermissionError("This website's robots.txt disallows fetching.")
            with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("The website returned an invalid redirect.")
                    current_url = urljoin(current_url, location)
                    continue
                response.raise_for_status()
                max_bytes = 1_000_000
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise ValueError("The website page is too large to enrich safely.")
                break
        else:
            raise ValueError("The website redirected too many times.")
    soup = BeautifulSoup(bytes(content), "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ", strip=True).split())[:4000]
    cache_set(cache_key, text, FETCH_CACHE_TTL)
    return text
