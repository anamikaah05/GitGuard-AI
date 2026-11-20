"""
models/loader.py — Model loading and caching

All three .pkl models are loaded once at application startup via the
`load_models()` lifespan function and stored in a module-level registry.
Every service accesses models through `get_model_registry()` rather than
loading from disk on each request.
"""

from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import joblib

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ModelRegistry:
    """Container that holds references to all loaded ML artefacts."""
    secret_model: Any = field(default=None)
    tfidf_vectorizer: Any = field(default=None)
    pr_risk_model: Any = field(default=None)

    @property
    def all_loaded(self) -> bool:
        return all([
            self.secret_model is not None,
            self.tfidf_vectorizer is not None,
            self.pr_risk_model is not None,
        ])

    def status(self) -> dict[str, bool]:
        return {
            "secret_model": self.secret_model is not None,
            "tfidf_vectorizer": self.tfidf_vectorizer is not None,
            "pr_risk_model": self.pr_risk_model is not None,
        }


# Module-level singleton registry
_registry: ModelRegistry = ModelRegistry()


def _resolve_path(raw: str) -> Path:
    """Resolve a path relative to the backend/ directory."""
    p = Path(raw)
    if not p.is_absolute():
        # Resolve relative to the directory that contains this file
        p = (Path(__file__).parent.parent / raw).resolve()
    return p


def load_models() -> None:
    """
    Load all ML models from disk into the registry.

    Called once during FastAPI application startup via the lifespan context
    manager in main.py.  Raises FileNotFoundError if a model file is missing.
    """
    global _registry

    paths = {
        "secret_model": _resolve_path(settings.secret_model_path),
        "tfidf_vectorizer": _resolve_path(settings.tfidf_vectorizer_path),
        "pr_risk_model": _resolve_path(settings.pr_risk_model_path),
    }

    for attr, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Model file not found: {path}. "
                f"Check the path configured for '{attr.upper()}_PATH' in .env"
            )
        logger.info("Loading model '%s' from %s …", attr, path)
        setattr(_registry, attr, joblib.load(path))
        logger.info("✓ '%s' loaded successfully.", attr)


def get_model_registry() -> ModelRegistry:
    """Return the shared model registry (dependency-injection style)."""
    return _registry
