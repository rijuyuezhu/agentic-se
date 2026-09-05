from __future__ import annotations

from typing import Any

from taskforge import service
from taskforge.model import Job


def _view(job: Job) -> dict[str, Any]:
    """Return a detached, serialization-friendly public view.

    M04 deliberately starts with a boundary that fixes one M02 problem
    (representation exposure) while leaving several semantic problems unresolved.
    """

    return {
        "id": job.id,
        "command": job.command,
        "status": job.status.value,
        "exit_code": job.exit_code,
    }


def submit_job(command: str) -> dict[str, Any]:
    """Submit a job through the intentionally shallow M04 boundary.

    Current behavior deliberately has no explicit input-domain or retry contract.
    """

    job_id = service.submit(command)
    return {"job_id": job_id}


def get_job(job_id: str) -> dict[str, Any]:
    """Get a public job view.

    Unknown IDs currently leak the service layer's KeyError.
    """

    return _view(service.get(job_id))


def list_jobs() -> list[dict[str, Any]]:
    return [_view(job) for job in service.list_jobs()]


def cancel_job(job_id: str) -> dict[str, Any]:
    """Attempt cancellation.

    The boolean deliberately collapses several semantically different states,
    while an unknown ID still raises KeyError. M04 asks the student to redesign
    this contract before making the implementation more elaborate.
    """

    return {"cancelled": service.cancel(job_id)}
