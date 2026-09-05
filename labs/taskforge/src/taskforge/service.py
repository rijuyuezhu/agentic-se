from __future__ import annotations

from taskforge import state
from taskforge.model import Job, JobStatus


def submit(command: str) -> str:
    job_id = f"job-{state.next_job_number}"
    state.next_job_number += 1
    state.jobs[job_id] = Job(id=job_id, command=command)
    return job_id


def get(job_id: str) -> Job:
    """Return the job currently stored by TaskForge.

    M02 baseline deliberately returns the authoritative mutable object.
    The lab asks whether that is part of the intended abstraction.
    """
    return state.jobs[job_id]


def list_jobs() -> list[Job]:
    return list(state.jobs.values())


def cancel(job_id: str) -> bool:
    job = state.jobs[job_id]
    if job.terminal or job.status == JobStatus.RUNNING:
        return False
    job.status = JobStatus.CANCELLED
    return True


def reset_for_tests() -> None:
    # This is convenient, but it also demonstrates that tests are another writer.
    state.jobs.clear()
    state.next_job_number = 1
