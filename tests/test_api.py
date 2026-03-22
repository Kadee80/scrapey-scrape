from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture
def sample_html():
    return """
    <!doctype html>
    <html><head>
    <meta property="og:title" content="TestCo" />
    <meta property="og:description" content="We ship things." />
    </head><body><h1>Hi</h1></body></html>
    """


@patch("app.pipeline.fetch_html", new_callable=AsyncMock)
@patch("app.pipeline.check_robots_allowed", new_callable=AsyncMock)
def test_preview_robots_disallowed(mock_robots, mock_fetch, client):
    from app.scraper import RobotsStatus

    mock_robots.return_value = RobotsStatus(allowed=False, message="blocked")
    resp = client.post("/api/preview", json={"url": "https://example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["robots_allowed"] is False
    assert data["signals"]["coverage_score"] == 0.0


@patch("app.pipeline.fetch_html", new_callable=AsyncMock)
@patch("app.pipeline.check_robots_allowed", new_callable=AsyncMock)
def test_preview_success(mock_robots, mock_fetch, client, sample_html):
    from app.scraper import FetchResult, RobotsStatus

    mock_robots.return_value = RobotsStatus(allowed=True)
    mock_fetch.return_value = FetchResult(
        html=sample_html,
        final_url="https://example.com/",
        status_code=200,
    )
    resp = client.post(
        "/api/preview",
        json={"url": "https://example.com", "use_llm": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["robots_allowed"] is True
    assert data["signals"]["company_name"] == "TestCo"
    assert data["signals"]["coverage_score"] > 0


@patch("app.main.get_settings")
def test_push_without_notion_config(mock_gs, client):
    mock_gs.return_value = MagicMock(notion_token=None, notion_database_id=None)
    resp = client.post("/api/push", json={"url": "https://example.com"})
    assert resp.status_code == 503


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
