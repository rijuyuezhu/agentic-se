#!/usr/bin/env python3
"""Prepare the answer-leak-free Click worktree used by the Final Transfer Practicum."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

UPSTREAM = "https://github.com/pallets/click.git"
FROZEN_SHA = "333c28d79cd982990ee98eef61ec20ab1a4f38ba"
HISTORY_DEPTH = "3500"
WORK_BRANCH = "practicum-work"


def run(*args: str, cwd: Path | None = None, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--verify-tests",
        action="store_true",
        help="run the frozen full minimal pytest baseline after setup",
    )
    args = parser.parse_args()
    dest = args.destination.expanduser().resolve()

    if dest.exists():
        if any(dest.iterdir()):
            parser.error(f"destination is not empty: {dest}")
    else:
        dest.mkdir(parents=True)

    try:
        run("git", "init", "-q", cwd=dest)
        run("git", "remote", "add", "origin", UPSTREAM, cwd=dest)
        # Fetch the frozen object plus enough *past* history for archaeology. We
        # deliberately do not clone a branch or tags that could expose future fixes.
        run(
            "git",
            "fetch",
            "-q",
            f"--depth={HISTORY_DEPTH}",
            "origin",
            FROZEN_SHA,
            cwd=dest,
        )
        run("git", "checkout", "-q", "--detach", "FETCH_HEAD", cwd=dest)

        observed = run("git", "rev-parse", "HEAD", cwd=dest, capture=True)
        if observed != FROZEN_SHA:
            raise RuntimeError(f"frozen HEAD mismatch: {observed}")

        run("git", "remote", "remove", "origin", cwd=dest)
        run("git", "switch", "-q", "-c", WORK_BRANCH, cwd=dest)

        # Phase 1 requires a local checkpoint commit. Do not make the harness
        # depend on machine-global Git identity, but preserve one if configured.
        for key, fallback in (
            ("user.name", "Final Practicum Student"),
            ("user.email", "student@localhost.invalid"),
        ):
            configured = subprocess.run(
                ("git", "config", "--get", key),
                cwd=dest,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode == 0
            if not configured:
                run("git", "config", key, fallback, cwd=dest)

        # A future answer must not already be reachable from any provided ref.
        extra = run(
            "git", "rev-list", "--all", "--not", FROZEN_SHA, cwd=dest, capture=True
        )
        if extra:
            raise RuntimeError("unexpected commits outside the frozen history")

        remotes = run("git", "remote", cwd=dest, capture=True)
        if remotes:
            raise RuntimeError(f"unexpected remote remains: {remotes}")

        if args.verify_tests:
            run(
                "uv",
                "run",
                "--no-default-groups",
                "--group",
                "tests",
                "pytest",
                "-q",
                cwd=dest,
            )
    except Exception:
        # Do not leave a half-prepared worktree that looks trustworthy.
        if dest.exists():
            shutil.rmtree(dest)
        raise

    history_count = run("git", "rev-list", "--count", "HEAD", cwd=dest, capture=True)
    print(f"Prepared: {dest}")
    print(f"Upstream provenance: {UPSTREAM}")
    print("Upstream license: BSD-3-Clause (see LICENSE.txt in the frozen checkout)")
    print(f"Frozen HEAD: {FROZEN_SHA}")
    print(f"Reachable pre-freeze commits: {history_count}")
    print("Remote removed: yes")
    print(f"Work branch: {WORK_BRANCH}")
    if not args.verify_tests:
        print("Next: uv run --no-default-groups --group tests pytest -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
