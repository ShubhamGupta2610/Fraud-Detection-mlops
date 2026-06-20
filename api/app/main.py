"""
Phase 0 entrypoint. Deliberately minimal - per ImplementationPlan.md,
Phase 0's only job is "empty-but-running skeleton with database
connectivity confirmed." Scoring logic, features, models: none of that
belongs here yet (Rules.md Rule 1 - don't build out of order).

Built async from the very first line, per TechSpec.md Section 2 and
ImplementationPlan.md Phase 4's note that retrofitting async later is
much harder than starting with it - even though Phase 0 doesn't need
async yet, the app object itself needs to be the async-capable kind
from day one.
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, engine, Base

# Importing models so Base.metadata knows about every table before
# create_all() runs. Importing for side-effect, not direct use here.
from app.models import transaction, operations  # noqa: F401

app = FastAPI(
    title="Adaptive Fraud & Risk Scoring Engine",
    version="0.1.0-phase0",
)


@app.on_event("startup")
def on_startup():
    """
    Creates all tables if they don't exist yet. Fine for local dev;
    a real migration tool (Alembic) is the correct upgrade before this
    ever touches a shared/production database - noting that now so it
    isn't forgotten later, rather than discovering it the hard way.
    """
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Per AppFlow.md Section 1 and TechSpec.md Section 5 - this is what
    a load balancer will poll later to know if a replica is healthy.
    Right now it does the simplest meaningful check: can we actually
    reach the database. Per Security.md Section 6, this must never leak
    internal detail (stack traces, connection strings) - so on failure
    it returns a flat "unhealthy" status, nothing more specific.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        return {"status": "unhealthy"}

    return {
        "status": "ok",
        "database": db_status,
    }


@app.get("/")
def root():
    return {
        "service": "Adaptive Fraud & Risk Scoring Engine",
        "phase": "0 - setup",
        "docs": "/docs",
    }
