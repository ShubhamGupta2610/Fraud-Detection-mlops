"""
SQLAlchemy models matching schema.md exactly.

Why these specific tables and not "however the ORM defaults would shape
it": schema.md was designed deliberately (e.g. scores.replica_id and
latency_ms exist specifically to feed the System Health dashboard panel
and the load-test evidence in Tracker.md). Following it precisely now
avoids a painful migration later.
"""

import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from app.db.session import Base
import enum


def gen_uuid():
    return str(uuid.uuid4())


class DecisionEnum(str, enum.Enum):
    allow = "allow"
    challenge = "challenge"
    block = "block"


class Transaction(Base):
    """schema.md Section 1"""
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    account_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    merchant_category = Column(String, nullable=False)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    device_id = Column(String, nullable=True)
    raw_features_json = Column(JSONB, nullable=True)


class Score(Base):
    """schema.md Section 2"""
    __tablename__ = "scores"

    score_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    transaction_id = Column(UUID(as_uuid=False), ForeignKey("transactions.transaction_id"), nullable=False)
    model_version = Column(String, index=True, nullable=False)
    risk_score = Column(Float, nullable=False)  # 0-100
    decision = Column(Enum(DecisionEnum), nullable=False)
    threshold_used = Column(Float, nullable=False)
    shap_top_features_json = Column(JSONB, nullable=True)
    scored_at = Column(DateTime(timezone=True), server_default=func.now())

    # Added specifically to make scale claims checkable per Security/Tracker design:
    replica_id = Column(String, nullable=True)
    latency_ms = Column(Float, nullable=True)
