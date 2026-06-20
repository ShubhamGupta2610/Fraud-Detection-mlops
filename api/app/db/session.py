"""
Database engine and session setup.

Why pooling is configured explicitly here (TechSpec.md Section 6.4):
Without a bounded pool, every request would open a brand-new raw Postgres
connection - fine at 10 users, a real bottleneck at 10,000 concurrent
requests. SQLAlchemy's pool reuses a bounded set of connections instead.

pool_size / max_overflow are intentionally modest for local dev. Phase 9
(load testing) is where we actually tune these numbers against real
measured behavior instead of guessing - see Tracker.md Section 4.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # detects dead connections instead of failing requests on them
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency - yields a session, always closes it after the
    request, even if the request raises an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
