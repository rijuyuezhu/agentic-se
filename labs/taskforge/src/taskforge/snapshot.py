from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from taskforge import service


SCHEMA_VERSION = 1


class SnapshotFormatError(ValueError):
    pass


@dataclass(frozen=True)
class SnapshotJob:
    id: str
    command: str
    status: str
    exit_code: int | None


@dataclass(frozen=True)
class Snapshot:
    schema_version: int
    jobs: tuple[SnapshotJob, ...]


def _decode_job(raw: object) -> SnapshotJob:
    if not isinstance(raw, dict):
        raise SnapshotFormatError("snapshot job must be an object")
    try:
        job_id = raw["id"]
        command = raw["command"]
        status = raw["status"]
        exit_code = raw["exit_code"]
    except KeyError as exc:
        raise SnapshotFormatError(f"missing snapshot field: {exc.args[0]}") from None

    if not isinstance(job_id, str) or not isinstance(command, str) or not isinstance(status, str):
        raise SnapshotFormatError("snapshot id, command, and status must be strings")
    if exit_code is not None and not isinstance(exit_code, int):
        raise SnapshotFormatError("snapshot exit_code must be an integer or null")

    return SnapshotJob(
        id=job_id,
        command=command,
        status=status,
        exit_code=exit_code,
    )


def loads_snapshot(text: str) -> Snapshot:
    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SnapshotFormatError(f"invalid JSON: {exc.msg}") from None

    if not isinstance(raw, dict):
        raise SnapshotFormatError("snapshot root must be an object")

    version = raw.get("schema_version")
    if version != SCHEMA_VERSION:
        raise SnapshotFormatError(
            f"unsupported snapshot schema_version: {version!r}; expected {SCHEMA_VERSION}"
        )

    jobs = raw.get("jobs")
    if not isinstance(jobs, list):
        raise SnapshotFormatError("snapshot jobs must be an array")

    return Snapshot(schema_version=version, jobs=tuple(_decode_job(job) for job in jobs))


def dumps_current_snapshot() -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "jobs": [
            {
                "id": job.id,
                "command": job.command,
                "status": job.status.value,
                "exit_code": job.exit_code,
            }
            for job in service.list_jobs()
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def read_snapshot(path: str | Path) -> Snapshot:
    return loads_snapshot(Path(path).read_text(encoding="utf-8"))


def write_current_snapshot(path: str | Path) -> None:
    Path(path).write_text(dumps_current_snapshot(), encoding="utf-8")
