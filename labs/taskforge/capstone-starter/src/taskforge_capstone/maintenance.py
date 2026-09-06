from __future__ import annotations

from pathlib import Path

from taskforge_capstone.db import connect


def running_jobs_older_than(path: str | Path, *, before_created_at: float) -> list[str]:
    """Return running jobs old enough to deserve operator attention.

    The current background maintenance loop only observes; it does not recover
    jobs automatically because the v1 worker protocol has no attempt identity.
    """

    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT public_id
            FROM jobs
            WHERE status = 'running' AND created_at < ?
            ORDER BY id
            """,
            (before_created_at,),
        ).fetchall()
    return [str(row["public_id"]) for row in rows]


def operator_requeue(path: str | Path, job_id: str) -> bool:
    """Historical emergency action: put one running job back in the queue.

    This preserves an operational escape hatch, but it is not safe automatic
    crash recovery. A stale v1 worker can still finish the same logical job.
    """

    with connect(path) as conn:
        changed = conn.execute(
            """
            UPDATE jobs
            SET status = 'queued', worker_id = NULL
            WHERE public_id = ? AND status = 'running'
            """,
            (job_id,),
        ).rowcount
    return changed == 1
