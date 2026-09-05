from __future__ import annotations

import hashlib
import json
from pathlib import Path

from taskforge import service, snapshot, worker


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _legacy_v1_reader(text: str) -> list[tuple[str, str, str, int | None]]:
    """Frozen model of a deployed v1 consumer.

    The lab may change taskforge.snapshot, but this reader represents a consumer
    that has not been upgraded yet.
    """

    raw = json.loads(text)
    if raw.get("schema_version") != 1:
        raise ValueError(f"legacy reader only understands schema_version=1, got {raw.get('schema_version')!r}")

    jobs = []
    for item in raw["jobs"]:
        jobs.append((item["id"], item["command"], item["status"], item["exit_code"]))
    return jobs


def _historical_fixture() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "m08" / "snapshot-v1.json"


def historical_read_probe() -> None:
    text = _historical_fixture().read_text(encoding="utf-8")
    loaded = snapshot.loads_snapshot(text)
    assert loaded.schema_version == 1
    assert [job.id for job in loaded.jobs] == ["job-41", "job-42", "job-43"]
    assert [job.command for job in loaded.jobs] == [
        "echo historical",
        "false",
        "sleep 30",
    ]
    print(f"[OLD DATA READABLE] v1 fixture sha256={_fingerprint(text)}")


def legacy_reader_probe() -> None:
    service.reset_for_tests()

    ok = service.submit("true")
    worker.claim_next()
    worker.finish(ok, 0)

    failed = service.submit("false")
    worker.claim_next()
    worker.finish(failed, 9)

    service.submit("echo queued")

    text = snapshot.dumps_current_snapshot()
    legacy_jobs = _legacy_v1_reader(text)
    assert legacy_jobs == [
        ("job-1", "true", "succeeded", 0),
        ("job-2", "false", "failed", 9),
        ("job-3", "echo queued", "queued", None),
    ]
    print(f"[OLD READER ACCEPTS CURRENT WRITER] v1 output sha256={_fingerprint(text)}")


def naive_v2_cutover_probe() -> None:
    v2_text = json.dumps(
        {
            "schema_version": 2,
            "jobs": [
                {
                    "id": "job-1",
                    "task": {"kind": "shell", "command": "echo future"},
                    "status": "queued",
                    "exit_code": None,
                }
            ],
        },
        indent=2,
    ) + "\n"

    try:
        _legacy_v1_reader(v2_text)
    except (KeyError, ValueError) as exc:
        print(f"[EXPECTED BREAK] frozen v1 reader rejects v2: {type(exc).__name__}")
    else:
        raise AssertionError("the frozen v1 reader unexpectedly accepted the v2 format")

    try:
        snapshot.loads_snapshot(v2_text)
    except snapshot.SnapshotFormatError:
        print("[STARTER LIMIT] current TaskForge reader also rejects v2")
    else:
        raise AssertionError("starter reader was expected to reject v2")


def future_version_probe() -> None:
    future = '{"schema_version": 99, "jobs": []}'
    try:
        snapshot.loads_snapshot(future)
    except snapshot.SnapshotFormatError:
        print("[FAIL CLOSED] unknown future schema version is rejected")
    else:
        raise AssertionError("unknown future schema version should not be guessed")


def main() -> int:
    historical_read_probe()
    legacy_reader_probe()
    naive_v2_cutover_probe()
    future_version_probe()
    print("M08 compatibility baseline probe completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
