from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.extract_heuristic import extract_heuristic
from app.extract_llm import refine_with_openai
from app.models import ScrapedSignals


@pytest.mark.asyncio
async def test_refine_with_openai_returns_false_when_api_raises():
    base = ScrapedSignals(
        company_name="Co",
        source_url="https://example.com",
        coverage_score=0.5,
    )
    with (
        patch("app.extract_llm.get_settings") as mock_settings,
        patch("openai.AsyncOpenAI") as mock_client_cls,
    ):
        mock_settings.return_value.openai_api_key = "sk-test"
        mock_settings.return_value.openai_model = "gpt-4o-mini"
        mock_create = AsyncMock(side_effect=RuntimeError("API down"))
        mock_client_cls.return_value.chat.completions.create = mock_create

        out, used = await refine_with_openai("some text", base)

        assert used is False
        assert out.company_name == "Co"
        assert out.extraction_method == "heuristic"


@pytest.mark.asyncio
async def test_refine_with_openai_returns_true_on_success():
    html = "<html><head><meta property='og:title' content='X'/></head><body></body></html>"
    base = extract_heuristic(html, "https://example.com/")
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content='{"company_name": "Y"}'))]

    with (
        patch("app.extract_llm.get_settings") as mock_settings,
        patch("openai.AsyncOpenAI") as mock_client_cls,
    ):
        mock_settings.return_value.openai_api_key = "sk-test"
        mock_settings.return_value.openai_model = "gpt-4o-mini"
        mock_client_cls.return_value.chat.completions.create = AsyncMock(return_value=mock_resp)

        out, used = await refine_with_openai("page text", base)

        assert used is True
        assert out.company_name == "Y"
        assert out.extraction_method == "hybrid"
