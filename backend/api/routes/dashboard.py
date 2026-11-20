"""
GitGuard AI Dashboard API.
Provides real scan statistics and recent scan history.
"""

from fastapi import APIRouter
from sqlalchemy import func

from database.connnection import SessionLocal
from database.model import ScanHistory

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


# --------------------------------------------------
# DASHBOARD STATISTICS
# --------------------------------------------------

@router.get("/stats")
def get_dashboard_stats():

    db = SessionLocal()

    try:
        total_scans = (
            db.query(func.count(ScanHistory.id)).scalar() or 0
        )

        secrets_detected = (
            db.query(func.count(ScanHistory.id))
            .filter(ScanHistory.has_secret == True)
            .scalar() or 0
        )

        safe_scans = (
            db.query(func.count(ScanHistory.id))
            .filter(ScanHistory.has_secret == False)
            .scalar() or 0
        )

        risky_prs = (
            db.query(func.count(ScanHistory.id))
            .filter(
                ScanHistory.event_type == "pull_request",
                ScanHistory.risk_level.in_(["HIGH", "MEDIUM"])
            )
            .scalar() or 0
        )

        push_scans = (
            db.query(func.count(ScanHistory.id))
            .filter(ScanHistory.event_type == "push")
            .scalar() or 0
        )

        pr_scans = (
            db.query(func.count(ScanHistory.id))
            .filter(ScanHistory.event_type == "pull_request")
            .scalar() or 0
        )

        return {
            "total_scans": total_scans,
            "secrets_detected": secrets_detected,
            "risky_prs": risky_prs,
            "safe_scans": safe_scans,
            "push_scans": push_scans,
            "pr_scans": pr_scans,
        }

    finally:
        db.close()


# --------------------------------------------------
# RECENT SCAN HISTORY
# --------------------------------------------------

@router.get("/scans")
def get_recent_scans(limit: int = 10):

    db = SessionLocal()

    try:
        scans = (
            db.query(ScanHistory)
            .order_by(ScanHistory.created_at.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )

        return {
            "total": len(scans),
            "scans": [
                {
                    "id": scan.id,
                    "repository": scan.repository,
                    "event_type": scan.event_type,
                    "action": scan.action,
                    "branch": scan.branch,
                    "pr_url": scan.pr_url,
                    "has_secret": scan.has_secret,
                    "ml_prediction": scan.ml_prediction,
                    "secret_confidence": scan.secret_confidence,
                    "rule_findings": scan.rule_findings,
                    "entropy_findings": scan.entropy_findings,
                    "risk_level": scan.risk_level,
                    "risk_confidence": scan.risk_confidence,
                    "files_scanned": scan.files_scanned,
                    "scan_status": scan.scan_status,
                    "created_at": (
                        scan.created_at.isoformat()
                        if scan.created_at else None
                    ),
                }
                for scan in scans
            ],
        }

    finally:
        db.close()