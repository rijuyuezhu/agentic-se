from __future__ import annotations

from taskforge import state
from taskforge.model import JobStatus


def queued_count() -> int:
    return sum(job.status == JobStatus.QUEUED for job in state.jobs.values())


def terminal_count() -> int:
    return sum(job.terminal for job in state.jobs.values())
