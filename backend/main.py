"""
main.py — GitGuard AI FastAPI application entry point

Startup sequence:
  1. Load all three ML models into the ModelRegistry (via lifespan)
  2. Register CORS middleware (allows the React frontend to call the API)
  3. Register custom exception handlers
  4. Mount all API routers

Run with:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.exceptions import register_exception_handlers
from models.loader import load_models
from api.routes import health, secret_scan, pr_risk, pr_scan, github_webhook, dashboard
from database.connnection import create_tables

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load ML models on startup, release resources on shutdown."""

    logger.info("╔══════════════════════════════════════════╗")
    logger.info("║      GitGuard AI Backend — Starting      ║")
    logger.info("╚══════════════════════════════════════════╝")
    print("DATABASE STARTUP TEST",flush=True)
    # Create database tables
    create_tables()

    # Load ML models
    load_models()

    logger.info("All models loaded. API is ready.")

    yield

    logger.info("GitGuard AI Backend — Shutting down.")


# ── FastAPI application ────────────────────────────────────────────────────────
app = FastAPI(
    title="GitGuard AI API",
    description=(
        "AI-powered GitHub Secret & Risky Pull Request Detector.\n\n"
        "**Models in use:**\n"
        "- Secret Detection: TF-IDF + Logistic Regression (ProwlBench)\n"
        "- PR Risk Detection: Random Forest Classifier (SEVRA)\n\n"
        "**Rule-based layers:**\n"
        "- Regex pattern matching for 20+ secret types\n"
        "- Shannon entropy analysis for high-entropy token detection"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom exception handlers ─────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(secret_scan.router)
app.include_router(pr_risk.router)
app.include_router(pr_scan.router)
app.include_router(github_webhook.router)
app.include_router(dashboard.router)


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
