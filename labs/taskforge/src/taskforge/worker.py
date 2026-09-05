from __future__ import annotations

from taskforge import state
from taskforge.model import Job, JobStatus


def claim_next() -> Job | None:
    """Claim the first queued job in insertion order."""
    for job in state.jobs.values():
        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.RUNNING
            return job
    return None


def finish(job_id: str, exit_code: int) -> None:
    job = state.jobs[job_id]
    if job.status != JobStatus.RUNNING:
        raise ValueError(f"cannot finish {job_id} from {job.status.value}")
    job.exit_code = exit_code
    job.status = JobStatus.SUCCEEDED if exit_code == 0 else JobStatus.FAILED
