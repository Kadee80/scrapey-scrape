from __future__ import annotations

from datetime import date

from notion_client import Client

from app.models import ScrapedSignals
from app.settings import get_settings


def _rich_text(content: str) -> dict:
    text = (content or "")[:2000] or " "
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": text},
            }
        ]
    }


def _title(content: str) -> dict:
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": content[:2000] or "Untitled"},
            }
        ]
    }


def _url_val(u: str) -> dict:
    return {"url": u[:2000]}


def _number_val(n: float) -> dict:
    return {"number": round(n, 3)}


def _date_val(d: date) -> dict:
    return {"date": {"start": d.isoformat()}}


def push_to_notion(signals: ScrapedSignals) -> tuple[str | None, str | None]:
    settings = get_settings()
    if not settings.notion_token or not settings.notion_database_id:
        raise ValueError(
            "Notion is not configured. Set NOTION_TOKEN and NOTION_DATABASE_ID in .env"
        )

    client = Client(auth=settings.notion_token, notion_version="2022-06-28")

    title = signals.company_name or signals.description or signals.source_url or "Prospect"
    emails_joined = ", ".join(signals.emails[:20])
    phones_joined = ", ".join(signals.phones[:20])
    social_joined = "\n".join(f"{k}: {v}" for k, v in signals.social_urls.items())

    props = {
        settings.notion_prop_title: _title(title),
        settings.notion_prop_source_url: _url_val(signals.source_url),
        settings.notion_prop_description: _rich_text(signals.description or ""),
        settings.notion_prop_industry: _rich_text(signals.industry or ""),
        settings.notion_prop_location: _rich_text(signals.location or ""),
        settings.notion_prop_emails: _rich_text(emails_joined),
        settings.notion_prop_phones: _rich_text(phones_joined),
        settings.notion_prop_social: _rich_text(social_joined),
        settings.notion_prop_funding: _rich_text(signals.funding_or_size_hint or ""),
        settings.notion_prop_coverage: _number_val(signals.coverage_score),
        settings.notion_prop_scraped_at: _date_val(signals.scraped_at.date()),
        settings.notion_prop_method: _rich_text(signals.extraction_method),
    }

    page = client.pages.create(
        parent={"database_id": settings.notion_database_id},
        properties=props,
    )
    page_id = page.get("id")
    notion_url = page.get("url")
    return page_id, notion_url
