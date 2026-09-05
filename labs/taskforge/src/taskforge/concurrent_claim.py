from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from taskforge import state
from taskforge.model import JobStatus


@dataclass(frozen=True)
class ClaimReceipt:
    job_id: str
    worker_id: str


# Teaching-only ownership registry.  The deliberately unsafe starter keeps
# lifecycle state and owner information in separate mutable locations.
claim_owners: dict[str, str] = {}


def claim_next(
    worker_id: str,
    *,
    after_observe: Callable[[str, str], None] | None = None,
) -> ClaimReceipt | None:
    """Claim the first queued job.

    M07 starter deliberately splits observation from commit.  ``after_observe``
    is an explicit interleaving seam used by the deterministic teaching probe;
    it runs after QUEUED has been observed but before the state transition.
    """

    for job in state.jobs.values():
        if job.status != JobStatus.QUEUED:
            continue

        if after_observe is not None:
            after_observe(worker_id, job.id)

        # Deliberately unsafe check-then-act: another worker may have changed
        # the same job after our observation.
        job.status = JobStatus.RUNNING
        claim_owners[job.id] = worker_id
        return ClaimReceipt(job_id=job.id, worker_id=worker_id)

    return None


def owner_of(job_id: str) -> str | None:
    return claim_owners.get(job_id)


def reset_for_tests() -> None:
    claim_owners.clear()
