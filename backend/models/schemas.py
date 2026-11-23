"""
models/schemas.py — Pydantic request & response schemas

All API surface types are defined here. Keeping them in one place makes it
easy to evolve the contract without hunting across route files.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Shared enums ──────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SourceType(str, Enum):
    RAW_TEXT = "raw_text"
    GITHUB_URL = "github_url"


# ── Secret scan ───────────────────────────────────────────────────────────────

class SecretScanRequest(BaseModel):
    """Request body for POST /api/scan/secret"""
    text: Optional[str] = Field(
        default=None,
        description="Raw code/text snippet to scan for secrets.",
        examples=["GitHub App authentication is configured in backend settings."],
    )
    github_url: Optional[str] = Field(
        default=None,
        description="URL to a raw GitHub file (raw.githubusercontent.com) to fetch and scan.",
        examples=["https://raw.githubusercontent.com/owner/repo/main/.env"],
    )
    source: SourceType = Field(
        default=SourceType.RAW_TEXT,
        description="Indicates whether the content is provided directly or via a URL.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"text": "API_KEY=sk-abc123...", "source": "raw_text"},
                {"github_url": "https://raw.githubusercontent.com/owner/repo/main/config.py", "source": "github_url"},
            ]
        }
    }


class RuleMatch(BaseModel):
    """A single rule-based secret match."""
    secret_type: str = Field(..., description="Category of secret detected (e.g., 'GitHub Token').")
    matched_value: str = Field(..., description="The matched string (may be partially redacted).")
    line_number: Optional[int] = Field(default=None, description="Line number of the match (1-indexed).")


class SecretScanResponse(BaseModel):
    """Response body for POST /api/scan/secret"""
    has_secret: bool = Field(..., description="True if any secret was detected by ML or rules.")
    ml_prediction: str = Field(..., description="Raw ML model label: 'SECRET' or 'SAFE'.")
    confidence: float = Field(..., description="ML model confidence score (0.0–1.0).")
    rule_matches: list[RuleMatch] = Field(default_factory=list, description="Regex-based secret matches.")
    entropy_flags: list[str] = Field(default_factory=list, description="High-entropy tokens flagged as potential secrets.")
    scanned_text_length: int = Field(..., description="Number of characters in the scanned content.")


# ── PR risk scan ──────────────────────────────────────────────────────────────

class PRRiskRequest(BaseModel):
    """Request body for POST /api/scan/pr-risk"""
    pr_url: Optional[str] = Field(
        default=None,
        description="Full GitHub Pull Request URL (e.g., https://github.com/owner/repo/pull/42).",
        examples=["https://github.com/owner/repo/pull/42"],
    )
    diff_text: Optional[str] = Field(
        default=None,
        description="Raw PR unified diff text, used as an alternative to providing a PR URL.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"pr_url": "https://github.com/owner/repo/pull/42"},
                {"diff_text": "diff --git a/src/index.js ..."},
            ]
        }
    }


class PRFeatures(BaseModel):
    """Extracted features passed to the Random Forest model."""
    total_files_changed: int
    source_files: int
    test_files: int
    config_files: int
    lock_files: int


class PRRiskResponse(BaseModel):
    """Response body for POST /api/scan/pr-risk"""
    is_risky: bool = Field(..., description="True if the PR is classified as risky.")
    risk_level: RiskLevel = Field(..., description="Categorised risk level: LOW, MEDIUM, or HIGH.")
    confidence: float = Field(..., description="ML model confidence score (0.0–1.0).")
    features: PRFeatures = Field(..., description="The 5 features extracted from the PR diff and fed to the model.")
    model_used: str = Field(default="sevra_improved_random_forest", description="Name of the model used for inference.")


    # ── Combined PR security scan ─────────────────────────────────────────────────

class PRScanRequest(BaseModel):
    """Request body for POST /api/scan/pr"""
    pr_url: str = Field(
        ...,
        description="Full GitHub Pull Request URL.",
        examples=["https://github.com/owner/repo/pull/42"],
    )


class PRScanResponse(BaseModel):
    """Combined secret detection and PR risk scan response."""
    pr_url: str
    files_scanned: int
    files_skipped: int
    has_secret: bool
    secret_scan: SecretScanResponse
    pr_risk: PRRiskResponse


# ── Health check ──────────────────────────────────────────────────────────────

class ModelStatus(BaseModel):
    secret_model: bool
    tfidf_vectorizer: bool
    pr_risk_model: bool


class HealthResponse(BaseModel):
    status: str
    models_loaded: ModelStatus
    version: str = "1.0.0"
