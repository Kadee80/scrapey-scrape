from __future__ import annotations

import asyncio
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx

from app.settings import get_settings


@dataclass
class FetchResult:
    html: str
    final_url: str
    status_code: int


@dataclass
class RobotsStatus:
    allowed: bool
    message: str | None = None


def _robots_url(base: str) -> str:
    p = urlparse(base)
    return f"{p.scheme}://{p.netloc}/robots.txt"


async def check_robots_allowed(url: str) -> RobotsStatus:
    """Best-effort robots.txt check. If robots.txt is missing or errors, allow with a note."""

    settings = get_settings()
    robots = _robots_url(url)

    def _parse() -> RobotsStatus:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots)
        try:
            rp.read()
        except Exception:
            return RobotsStatus(
                allowed=True,
                message="robots.txt unavailable or unreadable; proceeding with caution",
            )
        ua = settings.http_user_agent
        if rp.can_fetch(ua, url):
            return RobotsStatus(allowed=True, message=None)
        return RobotsStatus(
            allowed=False,
            message=f"URL disallowed for {ua.split('/')[0]} by robots.txt",
        )

    return await asyncio.to_thread(_parse)


async def fetch_html(url: str) -> FetchResult:
    settings = get_settings()
    headers = {
        "User-Agent": settings.http_user_agent,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype.lower() and "text" not in ctype.lower():
            # Some servers omit charset; still try if body looks like HTML
            text = resp.text[:500].lower()
            if "<html" not in text and "<!doctype html" not in text:
                raise ValueError(f"Unexpected content-type: {ctype or 'unknown'}")
        return FetchResult(html=resp.text, final_url=str(resp.url), status_code=resp.status_code)


def trim_visible_text(html: str, max_chars: int = 12000) -> str:
    """Cheap main-text extraction for LLM context (not full HTML)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [ln for ln in (ln.strip() for ln in text.splitlines()) if ln]
    out = "\n".join(lines)
    if len(out) > max_chars:
        return out[:max_chars] + "\n…"
    return out


def collect_href_links(html: str, base_url: str) -> list[str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        abs_url = urljoin(base_url, href)
        out.append(abs_url)
    return out
