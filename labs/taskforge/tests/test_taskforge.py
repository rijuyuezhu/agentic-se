from __future__ import annotations

import pytest

from taskforge import metrics, service, worker
from taskforge.model import JobStatus


@pytest.fixture(autouse=True)
def clean_state() -> None:
    service.reset_for_tests()


def test_submit_assigns_monotonic_ids_and_queues_jobs() -> None:
    first = service.submit("echo first")
    second = service.submit("echo second")

    assert first == "job-1"
    assert second == "job-2"
    assert [job.id for job in service.list_jobs()] == ["job-1", "job-2"]
    assert metrics.queued_count() == 2


def test_worker_claims_first_queued_job() -> None:
    first = service.submit("echo first")
    service.submit("echo second")

    claimed = worker.claim_next()

    assert claimed is not None
    assert claimed.id == first
    assert service.get(first).status == JobStatus.RUNNING
    assert metrics.queued_count() == 1


def test_worker_finishes_running_job() -> None:
    job_id = service.submit("true")
    worker.claim_next()

    worker.finish(job_id, 0)

    job = service.get(job_id)
    assert job.status == JobStatus.SUCCEEDED
    assert job.exit_code == 0
    assert metrics.terminal_count() == 1


def test_worker_records_failed_exit_code() -> None:
    job_id = service.submit("false")
    worker.claim_next()

    worker.finish(job_id, 7)

    job = service.get(job_id)
    assert job.status == JobStatus.FAILED
    assert job.exit_code == 7


def test_cancel_only_queued_job() -> None:
    queued = service.submit("sleep 1")
    running = service.submit("sleep 2")
    worker.claim_next()  # claims queued, so running is still queued
    worker.claim_next()  # now running is RUNNING

    assert service.cancel(queued) is False
    assert service.cancel(running) is False

    third = service.submit("sleep 3")
    assert service.cancel(third) is True
    assert service.get(third).status == JobStatus.CANCELLED


def test_finish_rejects_non_running_job() -> None:
    job_id = service.submit("true")

    with pytest.raises(ValueError, match="cannot finish"):
        worker.finish(job_id, 0)
