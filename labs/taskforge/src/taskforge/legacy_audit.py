from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import socket

from taskforge import state


def publish_daily_audit() -> str:
    """Append the current TaskForge state to the legacy daily audit file.

    This module is intentionally written in an old integration style for M06:
    it reaches directly into process environment, system time, hostname,
    filesystem, stdout, and TaskForge's in-memory state. There are no unit tests
    for it at the start of the lab.
    """

    root = Path(os.environ.get("TASKFORGE_AUDIT_DIR", ".taskforge-audit"))
    owner = os.environ.get("TASKFORGE_AUDIT_OWNER", "unknown")
    now = datetime.now(timezone.utc)
    hostname = socket.gethostname()
    jobs = list(state.jobs.values())

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"audit-{now:%Y-%m-%d}.log"

    lines = [
        f"== {now:%Y-%m-%dT%H:%M:%SZ} {hostname} owner={owner} ==",
        f"jobs={len(jobs)}",
    ]

    for index, job in enumerate(jobs, start=1):
        exit_code = "-" if job.exit_code is None else str(job.exit_code)
        lines.append(
            f"{index:02d} {job.id} {job.status.value:<9} "
            f"exit={exit_code} :: {job.command}"
        )

    block = "\n".join(lines) + "\n--\n"
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(block)

    print(f"audit: wrote {len(jobs)} job(s) -> {path}")
    return str(path)
