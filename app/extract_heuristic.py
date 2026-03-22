from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.models import ScrapedSignals
from app.scraper import collect_href_links

_SOCIAL_HOSTS = {
    "linkedin.com": "LinkedIn",
    "twitter.com": "X",
    "x.com": "X",
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "github.com": "GitHub",
    "youtube.com": "YouTube",
}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
)


def _meta_content(soup: BeautifulSoup, prop: str, attr: str = "property") -> str | None:
    tag = soup.find("meta", attrs={attr: prop}) or soup.find("meta", attrs={"name": prop})
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None


def _parse_json_ld_scripts(soup: BeautifulSoup) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for script in soup.find_all("script", type=lambda t: t and "ld+json" in t.lower()):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    found.append(item)
        elif isinstance(data, dict):
            found.append(data)
    return found


def _org_from_jsonld(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for b in blocks:
        t = b.get("@type")
        types = t if isinstance(t, list) else [t] if t else []
        type_strs = {str(x) for x in types}
        if not type_strs & {"Organization", "Corporation", "LocalBusiness", "WebSite"}:
            continue
        if "name" in b and not out.get("name"):
            out["name"] = b["name"]
        if "description" in b and not out.get("description"):
            out["description"] = b["description"]
        if "industry" in b and not out.get("industry"):
            out["industry"] = b["industry"]
        addr = b.get("address")
        if isinstance(addr, dict):
            parts = [
                addr.get("streetAddress"),
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("postalCode"),
                addr.get("addressCountry"),
            ]
            loc = ", ".join(str(p) for p in parts if p)
            if loc:
                out["location"] = loc
        elif isinstance(addr, str) and not out.get("location"):
            out["location"] = addr
        if "numberOfEmployees" in b and not out.get("employees"):
            out["employees"] = b["numberOfEmployees"]
        if "foundingDate" in b and not out.get("funding"):
            out["funding"] = str(b.get("foundingDate"))
    return out


def _coverage(signals: ScrapedSignals) -> float:
    weights = {
        "company_name": 0.2,
        "description": 0.2,
        "industry": 0.1,
        "location": 0.1,
        "emails": 0.15,
        "phones": 0.1,
        "social_urls": 0.15,
    }
    score = 0.0
    if signals.company_name:
        score += weights["company_name"]
    if signals.description and len(signals.description) > 20:
        score += weights["description"]
    if signals.industry:
        score += weights["industry"]
    if signals.location:
        score += weights["location"]
    if signals.emails:
        score += weights["emails"]
    if signals.phones:
        score += weights["phones"]
    if signals.social_urls:
        score += weights["social_urls"]
    return min(1.0, round(score, 3))


def extract_heuristic(html: str, source_url: str, company_hint: str | None = None) -> ScrapedSignals:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else None

    og_title = _meta_content(soup, "og:title") or _meta_content(soup, "twitter:title", "name")
    og_desc = _meta_content(soup, "og:description") or _meta_content(
        soup, "twitter:description", "name"
    )
    meta_desc = _meta_content(soup, "description", "name")

    h1 = soup.find("h1")
    h1_text = h1.get_text(strip=True) if h1 else None

    blocks = _parse_json_ld_scripts(soup)
    org = _org_from_jsonld(blocks)

    company_name = (
        company_hint
        or org.get("name")
        or og_title
        or h1_text
        or title_text
    )
    if company_name:
        company_name = company_name.strip()[:500]

    description = (
        org.get("description")
        or og_desc
        or meta_desc
    )
    if description:
        description = str(description).strip()[:4000]

    industry = org.get("industry")
    if industry:
        industry = str(industry).strip()[:500]

    location = org.get("location")
    if location:
        location = str(location).strip()[:500]

    emails: set[str] = set()
    for m in _EMAIL_RE.findall(soup.get_text(" ", strip=True)):
        emails.add(m.lower())

    phones: set[str] = set()
    for m in _PHONE_RE.findall(soup.get_text(" ", strip=True)):
        if len(re.sub(r"\D", "", m)) >= 10:
            phones.add(m.strip())

    social_urls: dict[str, str] = {}
    for link in collect_href_links(html, source_url):
        try:
            host = urlparse(link).netloc.lower()
        except Exception:
            continue
        for domain, label in _SOCIAL_HOSTS.items():
            if domain in host and label not in social_urls:
                social_urls[label] = link
                break

    funding_or_size = None
    if org.get("employees"):
        funding_or_size = f"Employees (structured): {org['employees']}"
    elif org.get("funding"):
        funding_or_size = str(org["funding"])

    signals = ScrapedSignals(
        company_name=company_name,
        description=description,
        industry=industry,
        location=location,
        emails=sorted(emails),
        phones=sorted(phones)[:8],
        social_urls=social_urls,
        funding_or_size_hint=funding_or_size,
        source_url=source_url,
        scraped_at=datetime.now(timezone.utc),
        coverage_score=0.0,
        extraction_method="heuristic",
    )
    signals.coverage_score = _coverage(signals)
    return signals
