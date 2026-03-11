from __future__ import annotations

import logging
import threading

from app import db as db_state
from app.config import get_settings
from app.models import AuditRun

logger = logging.getLogger(__name__)


def dispatch_audit_run(audit_run_id: int) -> str:
    settings = get_settings()
    if settings.execution_backend == "rq":
        from app.workers.queue import get_queue

        job = get_queue().enqueue("app.workers.tasks.run_audit_job", audit_run_id)
        return str(job.id)
    if settings.execution_backend == "inline":
        return start_inline_audit_run(audit_run_id)
    raise ValueError(f"Unsupported execution backend: {settings.execution_backend}")


def start_inline_audit_run(audit_run_id: int) -> str:
    thread_name = f"inline-audit-{audit_run_id}"
    thread = threading.Thread(
        target=_run_inline_audit_job,
        args=(audit_run_id,),
        name=thread_name,
        daemon=True,
    )
    thread.start()
    return thread_name


def _run_inline_audit_job(audit_run_id: int) -> None:
    from app.audit_engine.service import execute_audit_run

    with db_state.SessionLocal() as db:
        audit_run = db.get(AuditRun, audit_run_id)
        if audit_run is None:
            logger.warning("inline_audit_missing", extra={"audit_run_id": audit_run_id})
            return
        try:
            execute_audit_run(db, audit_run)
        except Exception:  # pragma: no cover - background thread guard
            logger.exception("inline_audit_failed", extra={"audit_run_id": audit_run_id})
