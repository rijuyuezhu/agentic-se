from __future__ import annotations

from pathlib import Path
from typing import Any

from taskforge_capstone import service


def submit_job(path: str | Path, command: str, *, now: float) -> dict[str, Any]:
    """Legacy public API used by an existing CLI client."""

    return {"job_id": service.submit(path, command, created_at=now)}


def get_job(path: str | Path, job_id: str) -> dict[str, Any]:
    job = service.get(path, job_id)
    return {
        "job_id": job["public_id"],
        "command": job["command"],
        "status": job["status"],
        "exit_code": job["exit_code"],
    }


def cancel_job(path: str | Path, job_id: str) -> dict[str, Any]:
    return {"cancelled": service.cancel(path, job_id)}
