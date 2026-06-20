"""
Central configuration, loaded entirely from environment variables.

Why this file exists (Security.md Section 3 + Rules.md Rule 17):
- No secret, credential, or connection string is ever hardcoded anywhere
  else in this codebase. Every other module imports `settings` from here
  instead of reading os.environ directly, so there is exactly ONE place
  secrets enter the program.
- Swapping local Postgres -> real Supabase later is just an env var change
  (DATABASE_URL), not a code change. That's the whole point of this layer.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- Database ---
    # Local dev default points at the docker-compose Postgres service.
    # In production this gets overridden by a real Supabase connection
    # string via an environment variable - never edited here.
    database_url: str = "postgresql://fraud_user:fraud_pass@localhost:5432/fraud_engine"

    # --- App behavior ---
    environment: str = "development"  # development | ci | production
    log_level: str = "INFO"

    # --- API behavior ---
    score_latency_target_ms: int = 100  # PRD.md Section 6 target, used in logging/alerts later
    default_risk_threshold: float = 0.5  # placeholder until the real cost-curve threshold is computed (TechSpec.md 5.4) - Rules.md Rule 7 says this must NOT stay hardcoded once that's built

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Cached so we don't re-parse environment variables on every call.
    Use as a FastAPI dependency later: Depends(get_settings)
    """
    return Settings()
