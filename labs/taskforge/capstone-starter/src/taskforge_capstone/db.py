from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize(path: str | Path) -> None:
    with connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                public_id TEXT NOT NULL UNIQUE,
                command TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
                ),
                worker_id TEXT,
                exit_code INTEGER,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS jobs_status_id_idx
                ON jobs(status, id);
            """
        )
        current = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if current == 0:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def schema_version(path: str | Path) -> int:
    with connect(path) as conn:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])


def job_columns(path: str | Path) -> list[str]:
    with connect(path) as conn:
        return [str(row[1]) for row in conn.execute("PRAGMA table_info(jobs)")]
