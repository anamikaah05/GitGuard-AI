"""
core/config.py — Centralised settings loaded from .env

All backend configuration is pulled from environment variables via
pydantic-settings. Add a `.env` file in the `backend/` directory
(copy from `.env.example`) before running the server.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    
    )
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]

    # ── Model paths ──────────────────────────────────────────────────────────
    secret_model_path: str = "../ml/saved_models/prowlbench_logistic_model.pkl"
    tfidf_vectorizer_path: str = "../ml/saved_models/prowlbench_tfidf_vectorizer.pkl"
    pr_risk_model_path: str = "../ml/saved_models/sevra_improved_random_forest.pkl"

    # ── GitHub integration ────────────────────────────────────────────────────
    # ── GitHub integration ────────────────────────────────────────────────────
    github_token: str = ""
    github_webhook_secret: str = ""

    # GitHub App authentication
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_installation_id: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
allowed_origins: str = "http://localhost:3000,http://localhost:5173"

@property
def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── App ───────────────────────────────────────────────────────────────────
app_env: str = "development"
log_level: str = "info"


# Single shared instance used throughout the app
settings = Settings()
