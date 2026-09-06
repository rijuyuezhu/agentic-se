from __future__ import annotations

import json
from pathlib import Path

import pytest

from taskforge_capstone import api, db, maintenance, remote_worker, service


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "taskforge.db"
    db.initialize(path)
    return path


def test_schema_starts_at_v1(database: Path) -> None:
    assert db.schema_version(database) == 1
    assert db.job_columns(database) == [
        "id",
        "public_id",
        "command",
        "status",
        "worker_id",
        "exit_code",
        "created_at",
    ]


def test_legacy_submit_api_shape_is_stable(database: Path) -> None:
    assert api.submit_job(database, "echo hello", now=100.0) == {"job_id": "job-1"}


def test_single_worker_claims_fifo(database: Path) -> None:
    first = service.submit(database, "first", created_at=1.0)
    second = service.submit(database, "second", created_at=2.0)

    claim = remote_worker.claim_next(database, "worker-a")

    assert claim == {"job_id": first, "command": "first"}
    assert service.get(database, first)["status"] == "running"
    assert service.get(database, second)["status"] == "queued"


def test_legacy_worker_finish_payload_still_works(database: Path) -> None:
    job_id = service.submit(database, "true", created_at=1.0)
    remote_worker.claim_next(database, "worker-a")

    fixture = Path(__file__).parents[1] / "fixtures" / "legacy-worker-finish.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["job_id"] = job_id

    assert remote_worker.finish_job(database, payload) is True
    assert service.get(database, job_id)["status"] == "succeeded"


def test_maintenance_only_observes_stale_running_jobs(database: Path) -> None:
    old_job = service.submit(database, "old", created_at=1.0)
    service.submit(database, "new", created_at=100.0)
    remote_worker.claim_next(database, "worker-a")

    assert maintenance.running_jobs_older_than(database, before_created_at=50.0) == [old_job]


def test_cancel_queued_job(database: Path) -> None:
    job_id = service.submit(database, "sleep 1", created_at=1.0)
    assert api.cancel_job(database, job_id) == {"cancelled": True}
    assert service.get(database, job_id)["status"] == "cancelled"
