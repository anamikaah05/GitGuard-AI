
"""
Combined GitHub Pull Request security scanning.
"""

import logging

from fastapi import APIRouter

from core.exceptions import InvalidInputError
from models.schemas import (
    PRScanRequest,
    PRScanResponse,
    PRRiskResponse,
    SecretScanResponse,
)
from services.pr_risk_service import predict_pr_risk
from services.secret_service import predict_secret
from scanner.scanner import run_rule_scan
from utils.github import fetch_pr_diff, fetch_pr_files

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/scan",
    tags=["Combined PR Security Scan"],
)


async def perform_pr_scan(pr_url: str) -> PRScanResponse:
    """Run the complete security scan for a GitHub PR."""

    logger.info("Fetching changed files for PR: %s", pr_url)

    files = await fetch_pr_files(pr_url)

    added_lines = []
    files_scanned = 0
    files_skipped = 0

    for file in files:
        patch = file.get("patch")

        if not patch:
            files_skipped += 1
            continue

        files_scanned += 1

        for line in patch.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added_lines.append(line[1:])

    code = "\n".join(added_lines)

    if not code.strip():
        raise InvalidInputError(
            "No newly added code was available to scan in this Pull Request."
        )

    rule_result = run_rule_scan(code)
    ml_result = predict_secret(code)

    has_secret = ml_result.is_secret or rule_result.has_findings

    secret_response = SecretScanResponse(
        has_secret=has_secret,
        ml_prediction=ml_result.ml_label,
        confidence=ml_result.confidence,
        rule_matches=rule_result.rule_matches,
        entropy_flags=rule_result.entropy_flags,
        scanned_text_length=len(code),
    )

    diff_text = await fetch_pr_diff(pr_url)

    if not diff_text.strip():
        raise InvalidInputError(
            "The Pull Request diff is empty. Nothing to analyse."
        )

    risk_result = predict_pr_risk(diff_text)

    risk_response = PRRiskResponse(
        is_risky=risk_result.is_risky,
        risk_level=risk_result.risk_level,
        confidence=risk_result.confidence,
        features=risk_result.features,
    )

    logger.info(
        "Combined PR scan complete | secret=%s | risk=%s",
        has_secret,
        risk_result.risk_level,
    )

    return PRScanResponse(
        pr_url=pr_url,
        files_scanned=files_scanned,
        files_skipped=files_skipped,
        has_secret=has_secret,
        secret_scan=secret_response,
        pr_risk=risk_response,
    )


@router.post(
    "/pr",
    response_model=PRScanResponse,
    summary="Perform a combined Pull Request security scan",
)
async def scan_pr(request: PRScanRequest) -> PRScanResponse:
    return await perform_pr_scan(request.pr_url)
