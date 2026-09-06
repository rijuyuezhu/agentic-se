from __future__ import annotations

from pathlib import Path

from taskforge_capstone.db import connect


def submit(path: str | Path, command: str, *, created_at: float) -> str:
    """Create one queued job and return its stable public id."""

    with connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        next_id = int(conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM jobs").fetchone()[0])
        public_id = f"job-{next_id}"
        conn.execute(
            """
            INSERT INTO jobs(id, public_id, command, status, worker_id, exit_code, created_at)
            VALUES (?, ?, ?, 'queued', NULL, NULL, ?)
            """,
            (next_id, public_id, command, created_at),
        )
        conn.commit()
        return public_id


def get(path: str | Path, job_id: str) -> dict[str, object]:
    with connect(path) as conn:
        row = conn.execute(
            """
            SELECT public_id, command, status, worker_id, exit_code, created_at
            FROM jobs
            WHERE public_id = ?
            """,
            (job_id,),
        ).fetchone()
    if row is None:
        raise KeyError(job_id)
    return dict(row)


def list_jobs(path: str | Path) -> list[dict[str, object]]:
    with connect(path) as conn:
        rows = conn.execute(
            """
            SELECT public_id, command, status, worker_id, exit_code, created_at
            FROM jobs
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def cancel(path: str | Path, job_id: str) -> bool:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT status FROM jobs WHERE public_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        if row["status"] != "queued":
            return False
        conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE public_id = ?",
            (job_id,),
        )
    return True
