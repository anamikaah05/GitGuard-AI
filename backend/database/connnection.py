import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Store the database inside the backend folder by default
BASE_DIR = Path(__file__).resolve().parent.parent

# Use DATABASE_URL if provided; otherwise use local SQLite
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'gitguard_scans.db'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# SQLite needs a special connection argument
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def create_tables():
    from database.model import ScanHistory

    Base.metadata.create_all(bind=engine)

    print("GitGuard AI database tables created successfully!")