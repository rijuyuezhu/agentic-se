from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


TASKFORGE_ROOT = Path(__file__).resolve().parents[1]
PATCH = TASKFORGE_ROOT / "review-cases" / "m10" / "agent-pr.patch"
DESCRIPTION = TASKFORGE_ROOT / "review-cases" / "m10" / "agent-pr-description.md"


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def _candidate_tree(temp_root: Path) -> Path:
    candidate = temp_root / "taskforge"
    shutil.copytree(
        TASKFORGE_ROOT,
        candidate,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"),
    )
    _run(["git", "init", "-q"], cwd=candidate)
    _run(["git", "apply", "--unidiff-zero", str(PATCH)], cwd=candidate)
    return candidate


def _python_env(candidate: Path) -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["PYTHONPATH"] = str(candidate / "src")
    return env


def author_ci(candidate: Path) -> int:
    result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
        ],
        cwd=candidate,
        env=_python_env(candidate),
        check=False,
    )
    print("[AUTHOR CI]")
    print(result.stdout.rstrip())
    if result.returncode != 0:
        print("candidate no longer reproduces the intended green-CI review case")
        return 1
    print("author-supplied CI is green")
    return 0


def reviewer_probes(candidate: Path) -> int:
    code = r'''
import json

from taskforge import public_api, service, snapshot, worker


def fresh_commands(n: int) -> list[str]:
    service.reset_for_tests()
    for index in range(1, n + 1):
        service.submit(f"cmd-{index}")
    return [job.id for job in service.list_jobs()]


findings = []

# Contract from M03: list_jobs preserves submission order.
observed = fresh_commands(12)
expected = [f"job-{i}" for i in range(1, 13)]
if observed != expected:
    findings.append({
        "id": "ordering-regression",
        "expected": expected,
        "observed": observed,
        "consequence": "list/snapshot/audit order is no longer submission order",
    })

# Contract from M03: claim_next is FIFO among queued jobs.
service.reset_for_tests()
ids = [service.submit(f"cmd-{i}") for i in range(1, 13)]
first = worker.claim_next()
second = worker.claim_next()
if first is None or second is None or [first.id, second.id] != ids[:2]:
    findings.append({
        "id": "fifo-regression",
        "expected": ids[:2],
        "observed": [None if first is None else first.id, None if second is None else second.id],
        "consequence": "scheduler no longer claims queued jobs in submission order",
    })

# The candidate calls itself behavior-preserving, but changes an existing
# public-boundary behavior from an exception to a successful-looking response.
service.reset_for_tests()
try:
    result = public_api.cancel_job("job-missing")
except KeyError:
    result = "KeyError"
if result != "KeyError":
    findings.append({
        "id": "undeclared-public-behavior-change",
        "expected": "KeyError (existing M04 baseline behavior)",
        "observed": result,
        "consequence": "the PR claims no public behavior change but changes the boundary contract",
    })

# Show a downstream durable-surface consequence of the same ordering bug.
service.reset_for_tests()
for index in range(1, 13):
    service.submit(f"cmd-{index}")
payload = json.loads(snapshot.dumps_current_snapshot())
snapshot_ids = [job["id"] for job in payload["jobs"]]
if snapshot_ids != expected:
    findings.append({
        "id": "snapshot-order-consequence",
        "expected": expected,
        "observed": snapshot_ids,
        "consequence": "the internal ordering change leaks into a durable exported artifact",
    })

print(json.dumps(findings, ensure_ascii=False, indent=2))
raise SystemExit(0 if findings else 2)
'''
    result = _run(
        [sys.executable, "-c", code],
        cwd=candidate,
        env=_python_env(candidate),
        check=False,
    )
    print("[REVIEWER PROBES]")
    print(result.stdout.rstrip())
    if result.returncode == 2:
        print("expected review findings were not reproduced")
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce the M10 green-CI candidate PR and optional reviewer probes."
    )
    parser.add_argument(
        "--reviewer-probes",
        action="store_true",
        help="Reveal high-information probes after you have written your own review.",
    )
    parser.add_argument(
        "--show-description",
        action="store_true",
        help="Print the author/Agent PR description before running the case.",
    )
    args = parser.parse_args()

    if args.show_description:
        print(DESCRIPTION.read_text(encoding="utf-8").rstrip())
        print()

    with tempfile.TemporaryDirectory(prefix="taskforge-m10-review-") as temp_dir:
        candidate = _candidate_tree(Path(temp_dir))
        if author_ci(candidate) != 0:
            return 1
        if args.reviewer_probes:
            return reviewer_probes(candidate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
