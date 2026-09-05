from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import os
from pathlib import Path
import tempfile

from taskforge import legacy_audit, service, worker


class FrozenDateTime:
    current = datetime(2026, 9, 6, 1, 2, 3, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):  # noqa: ANN001 - intentionally mimics datetime.now
        value = cls.current
        return value if tz is None else value.astimezone(tz)


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _run_once(root: Path) -> tuple[Path, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        path = Path(legacy_audit.publish_daily_audit())
    return path, stream.getvalue()


def _install_controlled_environment(root: Path) -> None:
    os.environ["TASKFORGE_AUDIT_DIR"] = str(root)
    os.environ["TASKFORGE_AUDIT_OWNER"] = "course-user"
    legacy_audit.datetime = FrozenDateTime  # type: ignore[assignment]
    legacy_audit.socket.gethostname = lambda: "lab-host"  # type: ignore[method-assign]


def scenario_empty(root: Path) -> tuple[str, str]:
    service.reset_for_tests()
    FrozenDateTime.current = datetime(2026, 9, 6, 1, 2, 3, tzinfo=timezone.utc)
    path, stdout = _run_once(root)
    return path.read_text(encoding="utf-8"), stdout


def scenario_mixed(root: Path) -> tuple[str, str]:
    service.reset_for_tests()

    succeeded = service.submit("true")
    worker.claim_next()
    worker.finish(succeeded, 0)

    failed = service.submit("false")
    worker.claim_next()
    worker.finish(failed, 7)

    cancelled = service.submit("sleep cancelled")
    service.cancel(cancelled)

    service.submit("echo queued")

    FrozenDateTime.current = datetime(2026, 9, 6, 4, 5, 6, tzinfo=timezone.utc)
    path, stdout = _run_once(root)
    return path.read_text(encoding="utf-8"), stdout


def scenario_append(root: Path) -> tuple[str, str]:
    service.reset_for_tests()
    service.submit("echo first")

    FrozenDateTime.current = datetime(2026, 9, 6, 8, 0, 0, tzinfo=timezone.utc)
    _, first_stdout = _run_once(root)

    service.submit("echo second")
    FrozenDateTime.current = datetime(2026, 9, 6, 8, 30, 0, tzinfo=timezone.utc)
    path, second_stdout = _run_once(root)

    return path.read_text(encoding="utf-8"), first_stdout + second_stdout


def main() -> int:
    old_datetime = legacy_audit.datetime
    old_hostname = legacy_audit.socket.gethostname
    old_dir = os.environ.get("TASKFORGE_AUDIT_DIR")
    old_owner = os.environ.get("TASKFORGE_AUDIT_OWNER")

    try:
        with tempfile.TemporaryDirectory(prefix="taskforge-m06-") as temp_dir:
            base = Path(temp_dir)
            results: list[tuple[str, str, str]] = []

            for name, scenario in (
                ("empty", scenario_empty),
                ("mixed", scenario_mixed),
                ("append", scenario_append),
            ):
                root = base / name
                _install_controlled_environment(root)
                file_text, stdout = scenario(root)
                results.append((name, file_text, stdout))

            expected_fragments = {
                "empty": [
                    "== 2026-09-06T01:02:03Z lab-host owner=course-user ==",
                    "jobs=0",
                    "--\n",
                ],
                "mixed": [
                    "jobs=4",
                    "01 job-1 succeeded exit=0 :: true",
                    "02 job-2 failed    exit=7 :: false",
                    "03 job-3 cancelled exit=- :: sleep cancelled",
                    "04 job-4 queued    exit=- :: echo queued",
                ],
                "append": [
                    "== 2026-09-06T08:00:00Z lab-host owner=course-user ==",
                    "jobs=1",
                    "== 2026-09-06T08:30:00Z lab-host owner=course-user ==",
                    "jobs=2",
                    "02 job-2 queued    exit=- :: echo second",
                ],
            }

            for name, file_text, stdout in results:
                for fragment in expected_fragments[name]:
                    if fragment not in file_text:
                        raise AssertionError(f"{name}: missing characterized fragment {fragment!r}")
                writes = 2 if name == "append" else 1
                if stdout.count("audit: wrote") != writes:
                    raise AssertionError(f"{name}: unexpected stdout behavior: {stdout!r}")
                normalized_stdout = stdout.replace(str(base / name), "<ROOT>")
                print(
                    f"[OK] {name}: file_sha256={_fingerprint(file_text)} "
                    f"stdout_sha256={_fingerprint(normalized_stdout)}"
                )

            print("legacy audit characterization probe passed")
            return 0
    finally:
        legacy_audit.datetime = old_datetime  # type: ignore[assignment]
        legacy_audit.socket.gethostname = old_hostname  # type: ignore[method-assign]
        if old_dir is None:
            os.environ.pop("TASKFORGE_AUDIT_DIR", None)
        else:
            os.environ["TASKFORGE_AUDIT_DIR"] = old_dir
        if old_owner is None:
            os.environ.pop("TASKFORGE_AUDIT_OWNER", None)
        else:
            os.environ["TASKFORGE_AUDIT_OWNER"] = old_owner


if __name__ == "__main__":
    raise SystemExit(main())
