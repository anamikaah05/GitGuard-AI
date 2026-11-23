
"""
core/config.py — Centralised settings loaded from .env
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General settings
    app_env: str = "development"
    log_level: str = "INFO"

    # CORS settings
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    # Model paths
    secret_model_path: str = "../ml/saved_models/prowlbench_logistic_model.pkl"
    tfidf_vectorizer_path: str = "../ml/saved_models/prowlbench_tfidf_vectorizer.pkl"
    pr_risk_model_path: str = "../ml/saved_models/sevra_improved_random_forest.pkl"

    # GitHub integration
    
    github_webhook_secret: str = ""

    # GitHub App authentication
    github_app_id: str = ""
    github_app_private_key_path: str = ""
    github_app_installation_id: str = ""


# Single shared instance
settings = Settings()
