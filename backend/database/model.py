from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text
from sqlalchemy.sql import func

from database.connnection import Base


class ScanHistory(Base):

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)

    # GitHub information
    repository = Column(String(255), nullable=True)
    event_type = Column(String(50), nullable=False)
    action = Column(String(50), nullable=True)
    branch = Column(String(255), nullable=True)
    pr_url = Column(String(500), nullable=True)
    commit_sha = Column(String(100), nullable=True)

    # Secret detection
    has_secret = Column(Boolean, default=False)
    ml_prediction = Column(String(50), nullable=True)
    secret_confidence = Column(Float, nullable=True)

    # Rule scanner
    rule_findings = Column(Integer, default=0)
    entropy_findings = Column(Integer, default=0)

    # PR risk detection
    risk_level = Column(String(50), nullable=True)
    risk_confidence = Column(Float, nullable=True)

    # Scan information
    files_scanned = Column(Integer, default=0)
    files_skipped = Column(Integer, default=0)
    scan_status = Column(String(50), default="completed")

    # Store complete scan response
    scan_details = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )