from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ScrapedSignals(BaseModel):
    """Structured client signals extracted from a single page."""

    company_name: str | None = None
    description: str | None = None
    industry: str | None = None
    location: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    social_urls: dict[str, str] = Field(default_factory=dict)
    funding_or_size_hint: str | None = None
    source_url: str = ""
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    coverage_score: float = 0.0
    extraction_method: Literal["heuristic", "llm", "hybrid"] = "heuristic"


class PreviewRequest(BaseModel):
    url: HttpUrl
    company_hint: str | None = None
    use_llm: bool = False
    coverage_threshold: float = Field(default=0.35, ge=0.0, le=1.0)


class PushRequest(PreviewRequest):
    """Same as preview; pushes to Notion after extraction."""


class PreviewResponse(BaseModel):
    signals: ScrapedSignals
    robots_allowed: bool = True
    robots_message: str | None = None
    llm_used: bool = False


class PushResponse(BaseModel):
    signals: ScrapedSignals
    notion_page_id: str | None = None
    notion_url: str | None = None
    robots_allowed: bool = True
    robots_message: str | None = None
    llm_used: bool = False


class HealthResponse(BaseModel):
    status: str = "ok"
