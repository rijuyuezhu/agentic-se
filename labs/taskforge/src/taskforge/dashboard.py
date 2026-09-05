from __future__ import annotations

from taskforge import service
from taskforge.model import JobStatus


def render_dashboard(title: str = "TaskForge Dashboard") -> str:
    """Render the intentionally entangled M05 text dashboard.

    The function is correct for its current contract, but it mixes domain
    interpretation (status classification and counts) with presentation. M05
    asks students to preserve this output exactly while changing the internal
    structure in preparation for a second renderer.
    """

    jobs = service.list_jobs()

    queued = 0
    running = 0
    succeeded = 0
    failed = 0
    cancelled = 0
    job_lines: list[str] = []

    for job in jobs:
        if job.status == JobStatus.QUEUED:
            queued += 1
            status_text = "queued"
        elif job.status == JobStatus.RUNNING:
            running += 1
            status_text = "running"
        elif job.status == JobStatus.SUCCEEDED:
            succeeded += 1
            status_text = f"succeeded({job.exit_code})"
        elif job.status == JobStatus.FAILED:
            failed += 1
            status_text = f"failed({job.exit_code})"
        elif job.status == JobStatus.CANCELLED:
            cancelled += 1
            status_text = "cancelled"
        else:  # pragma: no cover - defensive for future enum expansion
            raise ValueError(f"unknown job status: {job.status!r}")

        job_lines.append(f"{job.id} | {status_text} | {job.command}")

    total = len(jobs)
    active = queued + running
    terminal = succeeded + failed + cancelled

    lines = [
        title,
        f"total={total} active={active} terminal={terminal}",
        (
            f"queued={queued} running={running} succeeded={succeeded} "
            f"failed={failed} cancelled={cancelled}"
        ),
        "jobs:",
    ]

    if job_lines:
        lines.extend(job_lines)
    else:
        lines.append("<none>")

    return "\n".join(lines)
