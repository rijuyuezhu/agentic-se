from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

from taskforge_capstone.db import connect

ObserveHook = Callable[[str], None]


def claim_next(
    path: str | Path,
    worker_id: str,
    *,
    after_observe: ObserveHook | None = None,
) -> dict[str, object] | None:
    """Claim the first queued job using the historical v1 remote-worker protocol.

    The read and write are deliberately separate. The capstone begins with this
    known race rather than hiding it behind nondeterministic timing.
    """

    with connect(path) as conn:
        row = conn.execute(
            """
            SELECT id, public_id, command
            FROM jobs
            WHERE status = 'queued'
            ORDER BY id
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None

    if after_observe is not None:
        after_observe(str(row["public_id"]))

    with connect(path) as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'running', worker_id = ?
            WHERE id = ?
            """,
            (worker_id, int(row["id"])),
        )

    return {
        "job_id": str(row["public_id"]),
        "command": str(row["command"]),
    }


def finish_job(path: str | Path, payload: Mapping[str, object]) -> bool:
    """Apply the historical v1 completion payload.

    Old workers send only job_id + exit_code. There is intentionally no worker
    identity or attempt/lease token in this protocol.
    """

    job_id = str(payload["job_id"])
    exit_code = int(payload["exit_code"])
    status = "succeeded" if exit_code == 0 else "failed"

    with connect(path) as conn:
        changed = conn.execute(
            """
            UPDATE jobs
            SET status = ?, exit_code = ?
            WHERE public_id = ? AND status = 'running'
            """,
            (status, exit_code, job_id),
        ).rowcount
    return changed == 1
