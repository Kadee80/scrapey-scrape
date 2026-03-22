from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import HealthResponse, PreviewRequest, PreviewResponse, PushRequest, PushResponse
from app.pipeline import run_preview, run_push
from app.settings import get_settings

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    app = FastAPI(title="CRM Signals API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.post("/api/preview", response_model=PreviewResponse)
    async def preview(body: PreviewRequest) -> PreviewResponse:
        try:
            return await run_preview(
                str(body.url),
                body.company_hint,
                body.use_llm,
                body.coverage_threshold,
            )
        except httpx.HTTPError as e:
            logger.exception("preview fetch failed")
            raise HTTPException(status_code=502, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("preview failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.post("/api/push", response_model=PushResponse)
    async def push(body: PushRequest) -> PushResponse:
        settings = get_settings()
        if not settings.notion_token or not settings.notion_database_id:
            raise HTTPException(
                status_code=503,
                detail="Notion is not configured. Set NOTION_TOKEN and NOTION_DATABASE_ID in .env",
            )
        try:
            return await run_push(body)
        except ValueError as e:
            if "Notion is not configured" in str(e):
                raise HTTPException(status_code=503, detail=str(e)) from e
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("notion push failed")
            raise HTTPException(status_code=502, detail=str(e)) from e

    if FRONTEND_DIST.is_dir():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            if full_path.startswith("api"):
                raise HTTPException(status_code=404, detail="Not found")
            index = FRONTEND_DIST / "index.html"
            if index.is_file():
                return FileResponse(index)
            raise HTTPException(status_code=404, detail="Frontend not built")

    return app


app = create_app()
