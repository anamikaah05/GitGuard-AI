"""
api/routes/pr_risk.py — PR risk detection endpoint

POST /api/scan/pr-risk

Accepts either:
  - A GitHub Pull Request URL  → diff is fetched automatically via GitHub API
  - A raw unified diff string  → used directly

Runs the SEVRA-trained Random Forest Classifier on 5 extracted features and
returns a risk classification (LOW / MEDIUM / HIGH) with confidence score.
"""

import logging

from fastapi import APIRouter

from core.exceptions import InvalidInputError
from models.schemas import PRRiskRequest, PRRiskResponse
from services.pr_risk_service import predict_pr_risk
from utils.github import fetch_pr_diff

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scan", tags=["PR Risk Detection"])


@router.post(
    "/pr-risk",
    response_model=PRRiskResponse,
    summary="Classify a Pull Request as risky or safe",
    description=(
        "Extracts 5 structural features from the PR diff (total files changed, "
        "source/test/config/lock file counts) and runs them through a Random Forest "
        "classifier trained on the SEVRA dataset. "
        "Returns is_risky, risk_level (LOW/MEDIUM/HIGH), confidence, and the extracted features."
    ),
)
async def scan_pr_risk(request: PRRiskRequest) -> PRRiskResponse:
    # ── 1. Resolve the diff text ──────────────────────────────────────────────
    diff_text: str = ""

    if request.pr_url:
        logger.info("Fetching PR diff for: %s", request.pr_url)
        diff_text = await fetch_pr_diff(request.pr_url)

    elif request.diff_text:
        diff_text = request.diff_text

    else:
        raise InvalidInputError(
            "Provide either 'pr_url' (GitHub Pull Request URL) or 'diff_text' (raw unified diff)."
        )

    if not diff_text.strip():
        raise InvalidInputError("The resolved diff content is empty. Nothing to analyse.")

    # ── 2. ML prediction ──────────────────────────────────────────────────────
    result = predict_pr_risk(diff_text)

    logger.info(
        "PR risk scan complete | is_risky=%s | risk_level=%s | confidence=%.2f | features=%s",
        result.is_risky,
        result.risk_level,
        result.confidence,
        result.features,
    )

    return PRRiskResponse(
        is_risky=result.is_risky,
        risk_level=result.risk_level,
        confidence=result.confidence,
        features=result.features,
    )
