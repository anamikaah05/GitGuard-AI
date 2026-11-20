"""
services/pr_risk_service.py — ML inference for PR risk detection

Uses the SEVRA-trained Random Forest Classifier. The model expects exactly
5 numeric features, extracted from a PR diff:

    Feature            Description
    ─────────────────────────────────────────────────────────────
    total_files_changed  Total number of files touched in the diff
    source_files         Files with source code extensions (.py, .js, .ts, …)
    test_files           Files with test-related naming or extensions
    config_files         Configuration files (.env, .yaml, .json, .toml, …)
    lock_files           Dependency lock files (package-lock.json, etc.)

Risk level thresholds (applied to the RF's probability for class 1 / "risky"):
    0.0 – 0.40  → LOW
    0.40 – 0.70 → MEDIUM
    0.70 – 1.0  → HIGH
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import numpy as np

from core.exceptions import ModelNotLoadedError
from models.loader import get_model_registry
from models.schemas import PRFeatures, RiskLevel

logger = logging.getLogger(__name__)


# ── File classification helpers ───────────────────────────────────────────────

_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs",
    ".go", ".rb", ".php", ".swift", ".kt", ".rs", ".scala", ".r",
    ".html", ".css", ".scss", ".vue", ".svelte",
}

_CONFIG_EXTENSIONS = {
    ".env", ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".properties", ".plist", ".hcl", ".tf",
}

_LOCK_FILES = {
    "package-lock.json", "yarn.lock", "poetry.lock", "pipfile.lock",
    "composer.lock", "gemfile.lock", "cargo.lock", "go.sum",
}

_TEST_PATTERNS = re.compile(
    r"(test|spec|__tests__|_test\.|\.test\.|\.spec\.)",
    re.IGNORECASE,
)

_DIFF_FILE_HEADER = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def _classify_file(filename: str) -> dict[str, int]:
    """Return per-category counts for a single filename."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    base = filename.lower().split("/")[-1]  # basename only

    return {
        "source_files": int(ext in _SOURCE_EXTENSIONS),
        "test_files": int(bool(_TEST_PATTERNS.search(filename))),
        "config_files": int(ext in _CONFIG_EXTENSIONS),
        "lock_files": int(base in _LOCK_FILES),
    }


def extract_features(diff_text: str) -> PRFeatures:
    """
    Extract the 5 model features from a unified diff string.

    Parameters
    ----------
    diff_text: Raw unified diff (output of `git diff` or GitHub diff API).

    Returns
    -------
    PRFeatures ready to be passed to the Random Forest model.
    """
    filenames = _DIFF_FILE_HEADER.findall(diff_text)
    # Deduplicate (a file may appear multiple times in a large diff)
    filenames = list(dict.fromkeys(filenames))

    totals = {"source_files": 0, "test_files": 0, "config_files": 0, "lock_files": 0}
    for fname in filenames:
        cats = _classify_file(fname)
        for k in totals:
            totals[k] += cats[k]

    return PRFeatures(
        total_files_changed=len(filenames),
        source_files=totals["source_files"],
        test_files=totals["test_files"],
        config_files=totals["config_files"],
        lock_files=totals["lock_files"],
    )


# ── Risk level helper ─────────────────────────────────────────────────────────

def _risk_level(proba_risky: float) -> RiskLevel:
    if proba_risky >= 0.70:
        return RiskLevel.HIGH
    if proba_risky >= 0.40:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# ── Main service function ─────────────────────────────────────────────────────

@dataclass
class PRRiskPrediction:
    is_risky: bool
    risk_level: RiskLevel
    confidence: float
    features: PRFeatures


def predict_pr_risk(diff_text: str) -> PRRiskPrediction:
    """
    Classify a PR diff as risky or safe using the SEVRA Random Forest model.

    Parameters
    ----------
    diff_text: Raw unified diff text (from GitHub API or pasted by user).

    Returns
    -------
    PRRiskPrediction containing the risk label, level, confidence, and features.

    Raises
    ------
    ModelNotLoadedError: If the PR risk model has not been loaded.
    ValueError:          If *diff_text* is empty.
    """
    if not diff_text or not diff_text.strip():
        raise ValueError("diff_text must not be empty.")

    registry = get_model_registry()
    if registry.pr_risk_model is None:
        raise ModelNotLoadedError(
            "PR risk model is not loaded. "
            "Ensure load_models() was called at application startup."
        )

    features = extract_features(diff_text)

    # Build feature vector in the exact order the model was trained on:
    # ['total_files_changed', 'source_files', 'test_files', 'config_files', 'lock_files']
    X = np.array([[
        features.total_files_changed,
        features.source_files,
        features.test_files,
        features.config_files,
        features.lock_files,
    ]], dtype=float)

    label: int = int(registry.pr_risk_model.predict(X)[0])
    proba: np.ndarray = registry.pr_risk_model.predict_proba(X)[0]
    # proba[0] = P(safe=0), proba[1] = P(risky=1)
    proba_risky: float = float(proba[1])

    logger.debug(
        "PR risk scan: label=%d p_risky=%.4f features=%s",
        label, proba_risky, features,
    )

    return PRRiskPrediction(
        is_risky=bool(label == 1),
        risk_level=_risk_level(proba_risky),
        confidence=round(proba_risky if label == 1 else float(proba[0]), 4),
        features=features,
    )
