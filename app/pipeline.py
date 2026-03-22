from __future__ import annotations

import asyncio

from app.extract_heuristic import extract_heuristic
from app.extract_llm import refine_with_openai
from app.models import PreviewResponse, PushRequest, PushResponse, ScrapedSignals
from app.notion_push import push_to_notion
from app.scraper import check_robots_allowed, fetch_html, trim_visible_text
from app.settings import get_settings


async def run_preview(
    url: str,
    company_hint: str | None,
    use_llm: bool,
    coverage_threshold: float,
) -> PreviewResponse:
    settings = get_settings()
    robots = await check_robots_allowed(str(url))
    if not robots.allowed:
        empty = ScrapedSignals(source_url=str(url), coverage_score=0.0)
        return PreviewResponse(
            signals=empty,
            robots_allowed=False,
            robots_message=robots.message,
            llm_used=False,
        )

    fetched = await fetch_html(str(url))
    base = extract_heuristic(fetched.html, fetched.final_url, company_hint=company_hint)

    llm_used = False
    want_llm = use_llm or base.coverage_score < coverage_threshold
    if want_llm and settings.openai_api_key:
        text = trim_visible_text(fetched.html)
        base, llm_used = await refine_with_openai(text, base)

    return PreviewResponse(
        signals=base,
        robots_allowed=True,
        robots_message=robots.message,
        llm_used=llm_used,
    )


async def run_push(body: PushRequest) -> PushResponse:
    preview = await run_preview(
        str(body.url),
        body.company_hint,
        body.use_llm,
        body.coverage_threshold,
    )
    if not preview.robots_allowed:
        return PushResponse(
            signals=preview.signals,
            notion_page_id=None,
            notion_url=None,
            robots_allowed=False,
            robots_message=preview.robots_message,
            llm_used=preview.llm_used,
        )

    page_id, notion_url = await asyncio.to_thread(push_to_notion, preview.signals)
    return PushResponse(
        signals=preview.signals,
        notion_page_id=page_id,
        notion_url=notion_url,
        robots_allowed=True,
        robots_message=preview.robots_message,
        llm_used=preview.llm_used,
    )
