"""
api/routes/secret_scan.py — Secret detection endpoint

POST /api/scan/secret

Accepts either raw text or a GitHub file URL and runs:
  1. Rule-based scan  (regex patterns + Shannon entropy)
  2. ML classification (TF-IDF → Logistic Regression)

Both results are merged into a single SecretScanResponse.
"""

import logging

from fastapi import APIRouter

from core.exceptions import InvalidInputError
from models.schemas import SecretScanRequest, SecretScanResponse, SourceType
from scanner.scanner import run_rule_scan
from services.secret_service import predict_secret
from utils.github import fetch_raw_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scan", tags=["Secret Detection"])


@router.post(
    "/secret",
    response_model=SecretScanResponse,
    summary="Scan text or a GitHub file for secrets",
    description=(
        "Runs ML classification (TF-IDF + Logistic Regression trained on ProwlBench) "
        "and rule-based scanning (regex patterns + Shannon entropy) on the provided text. "
        "Returns whether a secret was detected, the confidence score, matched patterns, "
        "and high-entropy tokens."
    ),
)
async def scan_secret(request: SecretScanRequest) -> SecretScanResponse:
    # ── 1. Resolve the text to scan ──────────────────────────────────────────
    text: str = ""

    if request.source == SourceType.GITHUB_URL:
        if not request.github_url:
            raise InvalidInputError("github_url must be provided when source is 'github_url'.")
        logger.info("Fetching raw file from GitHub: %s", request.github_url)
        text = await fetch_raw_file(request.github_url)

    elif request.source == SourceType.RAW_TEXT:
        if not request.text:
            raise InvalidInputError("text must be provided when source is 'raw_text'.")
        text = request.text

    if not text.strip():
        raise InvalidInputError("The resolved text content is empty. Nothing to scan.")

    # ── 2. Rule-based scan ────────────────────────────────────────────────────
    rule_result = run_rule_scan(text)

    # ── 3. ML prediction ──────────────────────────────────────────────────────
    ml_result = predict_secret(text)

    # ── 4. Combine results ────────────────────────────────────────────────────
    # A secret is confirmed if either the ML model or rules detect one
    has_secret = ml_result.is_secret or rule_result.has_findings

    logger.info(
        "Secret scan complete | has_secret=%s | ml=%s (%.2f) | rule_matches=%d | entropy_flags=%d",
        has_secret,
        ml_result.ml_label,
        ml_result.confidence,
        len(rule_result.rule_matches),
        len(rule_result.entropy_flags),
    )

    return SecretScanResponse(
        has_secret=has_secret,
        ml_prediction=ml_result.ml_label,
        confidence=ml_result.confidence,
        rule_matches=rule_result.rule_matches,
        entropy_flags=rule_result.entropy_flags,
        scanned_text_length=len(text),
    )
