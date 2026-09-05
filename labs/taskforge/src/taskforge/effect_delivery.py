from __future__ import annotations

from collections.abc import Callable


class SimulatedCrash(RuntimeError):
    pass


completed_jobs: set[str] = set()


def deliver_once(
    job_id: str,
    effect: Callable[[str], None],
    *,
    crash_after_effect: bool = False,
) -> bool:
    """Deliver one external effect if local bookkeeping says it is incomplete.

    The name is intentionally stronger than the implementation can guarantee.
    M07 uses this function to expose the crash window between an external
    effect and independent local completion bookkeeping.
    """

    if job_id in completed_jobs:
        return False

    effect(job_id)

    if crash_after_effect:
        raise SimulatedCrash(f"simulated crash after external effect for {job_id}")

    completed_jobs.add(job_id)
    return True


def reset_for_tests() -> None:
    completed_jobs.clear()
