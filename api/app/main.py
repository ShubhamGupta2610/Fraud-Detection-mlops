"""
Phase 4 entrypoint — wires the model loader, feature cache, and
scoring router into the FastAPI app that Phase 0 created.

The app object itself (async-capable, created in Phase 0) is unchanged.
Phase 4 adds:
  1. A lifespan handler that loads the model at startup
  2. The /score, /feedback, /metrics, /drift-status, /retrain endpoints
     via the scoring router
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db, engine, Base
from app.models import transaction, operations  # noqa: F401 - registers tables with Base.metadata
from app.core.model_loader import load_model_and_explainer
from app.routers import scoring


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create tables + load the model.
    Shutdown: nothing needed (model is in memory, GC handles it).

    Using the modern lifespan context manager rather than the
    deprecated @app.on_event("startup") decorator from Phase 0 -
    FastAPI's own docs recommend this pattern as of 0.93+.
    """
    Base.metadata.create_all(bind=engine)
    load_model_and_explainer(app)
    yield


app = FastAPI(
    title="Adaptive Fraud & Risk Scoring Engine",
    version="0.4.0-phase4",
    lifespan=lifespan,
)

app.include_router(scoring.router, tags=["Scoring"])


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Load-balancer health check - per AppFlow.md and Security.md Section 6.
    Never leaks internal details on failure.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        return {"status": "unhealthy"}

    return {
        "status": "ok",
        "database": db_status,
        "model_version": getattr(app.state, "model_version", "not_loaded"),
    }


@app.get("/")
def root():
    return {
        "service": "Adaptive Fraud & Risk Scoring Engine",
        "phase": "4 - scoring API",
        "docs": "/docs",
        "endpoints": ["/score", "/feedback", "/metrics", "/drift-status", "/retrain", "/health"],
    }
