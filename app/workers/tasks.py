from __future__ import annotations

from app.audit_engine.service import execute_audit_run
from app import db as db_state
from app.models import AuditRun


def run_audit_job(audit_run_id: int) -> None:
    with db_state.SessionLocal() as db:
        audit_run = db.get(AuditRun, audit_run_id)
        if audit_run is None:
            return
        execute_audit_run(db, audit_run)
