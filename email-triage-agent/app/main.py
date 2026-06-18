"""
Smart Email Classifier & Rewriter — FastAPI microservice.

Two endpoints:
  POST /classify_email  -> categorize an email as Work/Personal/Finance/Spam
  POST /rewrite_email   -> rewrite an email in a requested tone

See README.md for setup instructions and prompts/templates.py for the
prompt engineering behind each endpoint.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.services.llm_client import LLMServiceError, call_llm
from app.logging_config import configure_logging
from app.models.schemas import (
    ClassifyEmailRequest,
    ClassifyEmailResponse,
    HealthResponse,
    RewriteEmailRequest,
    RewriteEmailResponse,
)
from app.services.templates import (
    CLASSIFICATION_CATEGORIES,
    CLASSIFICATION_SYSTEM_PROMPT,
    REWRITE_SYSTEM_PROMPT,
    build_classification_prompt,
    build_rewrite_prompt,
)

logger = logging.getLogger("email_ai_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting Smart Email AI service (model=%s)", settings.groq_model)
    yield
    logger.info("Shutting down Smart Email AI service")


app = FastAPI(
    title="Smart Email Classifier & Rewriter",
    description=(
        "A Gen-AI powered microservice that classifies emails into "
        "Work / Personal / Finance / Spam and rewrites emails in a "
        "requested tone using groq API."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

settings_for_cors = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"]
        if settings_for_cors.cors_origins == "*"
        else [o.strip() for o in settings_for_cors.cors_origins.split(",")]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    logger.error("LLM service error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_model=HealthResponse, tags=["Health"])
async def root() -> HealthResponse:
    """Basic health check + which LLM provider/model is configured."""
    settings = get_settings()
    return HealthResponse(status="ok", llm_provider=f"groq:{settings.groq_model}")


@app.post(
    "/classify_email",
    response_model=ClassifyEmailResponse,
    tags=["Email AI"],
    summary="Classify an email into Work, Personal, Finance, or Spam",
)
async def classify_email(payload: ClassifyEmailRequest) -> ClassifyEmailResponse:
    prompt = build_classification_prompt(payload.email_content)
    raw_result = call_llm(CLASSIFICATION_SYSTEM_PROMPT, prompt, max_tokens=16)

    cleaned = raw_result.strip().strip(".").strip()
    normalized = next(
        (c for c in CLASSIFICATION_CATEGORIES if c.lower() == cleaned.lower()),
        None,
    )

    if normalized is None:
        logger.warning(
            "LLM returned an unrecognized category %r; defaulting to closest match.",
            raw_result,
        )
        # Fall back to a substring match before giving up, since models
        # occasionally wrap the label in a short phrase despite instructions.
        normalized = next(
            (c for c in CLASSIFICATION_CATEGORIES if c.lower() in cleaned.lower()),
            "Spam",
        )

    logger.info("Classified email as %s", normalized)
    return ClassifyEmailResponse(category=normalized)  # type: ignore[arg-type]


@app.post(
    "/rewrite_email",
    response_model=RewriteEmailResponse,
    tags=["Email AI"],
    summary="Rewrite an email in a specified tone",
)
async def rewrite_email(payload: RewriteEmailRequest) -> RewriteEmailResponse:
    prompt = build_rewrite_prompt(payload.email_content, payload.tone)
    rewritten = call_llm(REWRITE_SYSTEM_PROMPT, prompt, max_tokens=1024)

    logger.info("Rewrote email in tone=%r (%d chars -> %d chars)",
                payload.tone, len(payload.email_content), len(rewritten))

    return RewriteEmailResponse(
        original_email=payload.email_content,
        tone=payload.tone,
        rewritten_email=rewritten,
    )


# Serve the minimal bonus frontend at /app (mounted last so it doesn't
# shadow the API routes above).
app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")