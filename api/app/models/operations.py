"""
Remaining tables from schema.md: feedback, model_runs, drift_checks,
load_test_runs. Kept in a separate file from transaction.py purely for
readability - they're all part of the same logical schema.
"""

import uuid
from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base
import enum


def gen_uuid():
    return str(uuid.uuid4())


class LabelEnum(str, enum.Enum):
    fraud = "fraud"
    legitimate = "legitimate"


class TriggerEnum(str, enum.Enum):
    scheduled = "scheduled"
    drift_triggered = "drift_triggered"
    manual = "manual"


class Feedback(Base):
    """schema.md Section 3 - the ground truth that feeds retraining"""
    __tablename__ = "feedback"

    feedback_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    transaction_id = Column(UUID(as_uuid=False), ForeignKey("transactions.transaction_id"), nullable=False)
    confirmed_label = Column(Enum(LabelEnum), nullable=False)
    source = Column(String, nullable=False)  # e.g. 'synthetic_generator', 'manual_review'
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelRun(Base):
    """schema.md Section 4 - every training run, not just the live one"""
    __tablename__ = "model_runs"

    run_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    version = Column(String, unique=True, index=True, nullable=False)
    trained_at = Column(DateTime(timezone=True), server_default=func.now())
    trigger_type = Column(Enum(TriggerEnum), nullable=False)
    pr_auc = Column(Float, nullable=True)
    promoted = Column(Boolean, default=False)
    artifact_path = Column(String, nullable=True)
    feedback_rows_used = Column(Integer, nullable=True)


class DriftCheck(Base):
    """schema.md Section 5 - PSI per feature, per scheduled check"""
    __tablename__ = "drift_checks"

    check_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    feature_name = Column(String, nullable=False)
    psi_value = Column(Float, nullable=False)
    alert_fired = Column(Boolean, default=False)


class LoadTestRun(Base):
    """schema.md Section 6 - the literal evidence store behind the 10K-user claim"""
    __tablename__ = "load_test_runs"

    test_id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    run_at = Column(DateTime(timezone=True), server_default=func.now())
    concurrent_users = Column(Integer, nullable=False)
    p50_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    p99_latency_ms = Column(Float, nullable=True)
    replica_count = Column(Integer, nullable=True)
    error_rate = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
