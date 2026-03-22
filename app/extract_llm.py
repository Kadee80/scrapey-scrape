from __future__ import annotations

import json
from typing import Any

from app.models import ScrapedSignals
from app.settings import get_settings


def _signals_to_dict(s: ScrapedSignals) -> dict[str, Any]:
    return json.loads(s.model_dump_json())


def _apply_llm_dict(base: ScrapedSignals, data: dict[str, Any]) -> ScrapedSignals:
    merged = base.model_copy(deep=True)
    if data.get("company_name"):
        merged.company_name = str(data["company_name"])[:500]
    if data.get("description"):
        merged.description = str(data["description"])[:4000]
    if data.get("industry"):
        merged.industry = str(data["industry"])[:500]
    if data.get("location"):
        merged.location = str(data["location"])[:500]
    if data.get("funding_or_size_hint"):
        merged.funding_or_size_hint = str(data["funding_or_size_hint"])[:1000]
    # Factual lists: keep heuristic wins
    merged.emails = list(dict.fromkeys(base.emails))
    merged.phones = list(dict.fromkeys(base.phones))
    if isinstance(data.get("social_urls"), dict):
        for k, v in data["social_urls"].items():
            if isinstance(v, str) and k not in merged.social_urls:
                merged.social_urls[str(k)] = v
    merged.extraction_method = "hybrid"
    return merged


async def refine_with_openai(visible_text: str, base: ScrapedSignals) -> ScrapedSignals:
    settings = get_settings()
    if not settings.openai_api_key:
        return base

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return base

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    schema_hint = {
        "company_name": "string or null",
        "description": "one or two sentences or null",
        "industry": "string or null",
        "location": "string or null",
        "funding_or_size_hint": "only if explicitly stated, else null",
        "social_urls": {"PlatformName": "url"},
    }
    prompt = (
        "You extract B2B prospecting signals from website text. "
        "Return ONLY valid JSON matching this shape (no markdown):\n"
        f"{json.dumps(schema_hint)}\n"
        "Use null when unknown. Do not invent emails or phone numbers.\n"
        "Base signals already found (prefer these for factual lists):\n"
        f"{json.dumps(_signals_to_dict(base), default=str)[:6000]}\n\n"
        "Page text:\n"
        f"{visible_text[:8000]}"
    )

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You output compact JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
    except Exception:
        return base
    if not isinstance(data, dict):
        return base
    merged = _apply_llm_dict(base, data)
    from app.extract_heuristic import _coverage  # noqa: PLC0415

    merged.coverage_score = _coverage(merged)
    return merged
