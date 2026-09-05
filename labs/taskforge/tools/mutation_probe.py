from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Mutant:
    name: str
    path: str
    old: str
    new: str
    claim: str


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        name="terminal_forgets_cancelled",
        path="src/taskforge/model.py",
        old="            JobStatus.CANCELLED,\n",
        new="",
        claim="CANCELLED is a terminal status.",
    ),
    Mutant(
        name="submit_drops_command",
        path="src/taskforge/service.py",
        old='    state.jobs[job_id] = Job(id=job_id, command=command)\n',
        new='    state.jobs[job_id] = Job(id=job_id, command="")\n',
        claim="submit preserves the command as observable job data.",
    ),
    Mutant(
        name="list_jobs_hides_terminal",
        path="src/taskforge/service.py",
        old="    return list(state.jobs.values())\n",
        new="    return [job for job in state.jobs.values() if not job.terminal]\n",
        claim="list_jobs includes terminal jobs, not only active jobs.",
    ),
    Mutant(
        name="finish_reverses_success_rule",
        path="src/taskforge/worker.py",
        old=(
            "    job.status = JobStatus.SUCCEEDED if exit_code == 0 "
            "else JobStatus.FAILED\n"
        ),
        new=(
            "    job.status = JobStatus.FAILED if exit_code == 0 "
            "else JobStatus.SUCCEEDED\n"
        ),
        claim="exit code 0 succeeds; nonzero exit codes fail.",
    ),
    Mutant(
        name="cancel_reports_success_without_transition",
        path="src/taskforge/service.py",
        old="    job.status = JobStatus.CANCELLED\n",
        new="    # mutant: report success but leave the state unchanged\n",
        claim="successful cancellation actually transitions the job to CANCELLED.",
    ),
    Mutant(
        name="claim_uses_lifo",
        path="src/taskforge/worker.py",
        old="    for job in state.jobs.values():\n",
        new="    for job in reversed(list(state.jobs.values())):\n",
        claim="if FIFO scheduling is part of the contract, claim_next chooses the oldest queued job.",
    ),
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def apply_mutant(root: Path, mutant: Mutant) -> None:
    target = root / mutant.path
    text = target.read_text(encoding="utf-8")
    count = text.count(mutant.old)
    if count != 1:
        raise RuntimeError(
            f"{mutant.name}: expected exactly one mutation site in {mutant.path}, found {count}"
        )
    target.write_text(text.replace(mutant.old, mutant.new, 1), encoding="utf-8")


def run_mutant(mutant: Mutant) -> dict[str, object]:
    source_root = project_root()
    with tempfile.TemporaryDirectory(prefix=f"taskforge-{mutant.name}-") as temp_dir:
        temp_root = Path(temp_dir)
        shutil.copytree(source_root / "src", temp_root / "src")
        shutil.copytree(source_root / "tests", temp_root / "tests")
        apply_mutant(temp_root, mutant)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp_root / "src")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=temp_root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    return {
        "name": mutant.name,
        "claim": mutant.claim,
        "status": "SURVIVED" if result.returncode == 0 else "KILLED",
        "returncode": result.returncode,
        "output": result.stdout.rstrip(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a small set of intentionally meaningful TaskForge mutants against "
            "the current test suite. This is a teaching probe, not a mutation score tool."
        )
    )
    parser.add_argument(
        "--mutant",
        action="append",
        choices=[mutant.name for mutant in MUTANTS],
        help="Run only the named mutant. May be repeated.",
    )
    parser.add_argument("--list", action="store_true", help="List mutants and exit.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    selected = [
        mutant
        for mutant in MUTANTS
        if args.mutant is None or mutant.name in set(args.mutant)
    ]

    if args.list:
        for mutant in selected:
            print(f"{mutant.name}: {mutant.claim}")
        return 0

    results = [run_mutant(mutant) for mutant in selected]

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(f"[{item['status']}] {item['name']}")
            print(f"  claim: {item['claim']}")
            output = str(item["output"])
            if output:
                for line in output.splitlines():
                    print(f"  | {line}")
            print()

        killed = sum(item["status"] == "KILLED" for item in results)
        survived = len(results) - killed
        print(f"summary: {killed} killed, {survived} survived")
        print("Interpret each survivor semantically; do not turn this into a percentage target.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
