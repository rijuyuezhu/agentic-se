from __future__ import annotations

from taskforge.model import Job

# M02 baseline: these globals are intentionally part of the design problem.
# Do not "fix" them before doing the read-only ownership analysis in the lab.
jobs: dict[str, Job] = {}
next_job_number: int = 1
