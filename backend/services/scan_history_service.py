import json

from database.connnection import SessionLocal
from database.model import ScanHistory


def save_scan_history(
    event_type: str,
    repository: str = None,
    action: str = None,
    branch: str = None,
    pr_url: str = None,
    commit_sha: str = None,
    has_secret: bool = False,
    ml_prediction: str = None,
    secret_confidence: float = None,
    rule_findings: int = 0,
    entropy_findings: int = 0,
    risk_level: str = None,
    risk_confidence: float = None,
    files_scanned: int = 0,
    files_skipped: int = 0,
    scan_details: dict = None,
):
    db = SessionLocal()

    try:
        record = ScanHistory(
            repository=repository,
            event_type=event_type,
            action=action,
            branch=branch,
            pr_url=pr_url,
            commit_sha=commit_sha,
            has_secret=has_secret,
            ml_prediction=ml_prediction,
            secret_confidence=secret_confidence,
            rule_findings=rule_findings,
            entropy_findings=entropy_findings,
            risk_level=risk_level,
            risk_confidence=risk_confidence,
            files_scanned=files_scanned,
            files_skipped=files_skipped,
            scan_details=json.dumps(scan_details) if scan_details else None,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return {
            "success": True,
            "scan_id": record.id,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()