from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db as db_state
from app.db import Base, configure_database

@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    configure_database(database_url)
    Base.metadata.create_all(bind=db_state.engine)
    monkeypatch.setattr("app.services.audits.build_inline_job_id", lambda _audit_run_id: "inline-audit-test")
    monkeypatch.setattr("app.routes.pages.start_inline_audit_run", lambda _audit_run_id, _job_id=None: "inline-audit-test")

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=db_state.engine)
