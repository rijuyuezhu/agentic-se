from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from taskforge import metrics, service, worker


@dataclass(frozen=True)
class JobLifecycleEvent:
    """One production-style lifecycle observation.

    M11 intentionally keeps this as an in-process teaching event rather than
    introducing a telemetry SDK.  The event shape is enough to reason about
    what a monitoring system could observe and what it might still miss.
    """

    event: str
    at_s: float
    job_id: str
    outcome: str | None = None


@dataclass(frozen=True)
class ProductionWindow:
    events: tuple[JobLifecycleEvent, ...]
    submitted: int
    succeeded: int
    ending_queue_depth: int


def run_deterministic_burst(
    *,
    job_count: int = 12,
    submit_spacing_s: float = 0.05,
    first_claim_at_s: float = 1.0,
    service_time_s: float = 1.0,
) -> ProductionWindow:
    """Run a deterministic burst against the baseline TaskForge lifecycle.

    The timeline is synthetic on purpose: M11 wants repeatable production
    reasoning, not a wall-clock benchmark.  All jobs are submitted first; one
    worker then claims and completes them sequentially.
    """

    service.reset_for_tests()
    events: list[JobLifecycleEvent] = []
    job_ids: list[str] = []

    for index in range(job_count):
        submitted_at = index * submit_spacing_s
        job_id = service.submit(f"work-{index + 1}")
        job_ids.append(job_id)
        events.append(JobLifecycleEvent("submitted", submitted_at, job_id))

    claim_at = first_claim_at_s
    for expected_job_id in job_ids:
        claimed = worker.claim_next()
        if claimed is None:
            raise AssertionError("deterministic burst unexpectedly ran out of queued jobs")
        if claimed.id != expected_job_id:
            raise AssertionError(
                f"baseline FIFO changed: expected {expected_job_id}, got {claimed.id}"
            )
        events.append(JobLifecycleEvent("claimed", claim_at, claimed.id))
        finished_at = claim_at + service_time_s
        worker.finish(claimed.id, 0)
        events.append(JobLifecycleEvent("finished", finished_at, claimed.id, "succeeded"))
        claim_at = finished_at

    return ProductionWindow(
        events=tuple(events),
        submitted=len(job_ids),
        succeeded=sum(job.outcome == "succeeded" for job in events if job.event == "finished"),
        ending_queue_depth=metrics.queued_count(),
    )


def naive_health_summary(window: ProductionWindow) -> dict[str, float | int | bool]:
    """A deliberately insufficient production dashboard for M11.

    It asks only whether accepted work eventually succeeded and whether the
    queue happened to be empty at the end of the observation window.
    """

    success_ratio = window.succeeded / window.submitted if window.submitted else 1.0
    healthy = success_ratio >= 0.99 and window.ending_queue_depth <= 2
    return {
        "submitted": window.submitted,
        "success_ratio": success_ratio,
        "ending_queue_depth": window.ending_queue_depth,
        "healthy": healthy,
    }


def naive_metric_labelsets(window: ProductionWindow) -> set[tuple[tuple[str, str], ...]]:
    """Return the metric series produced by a deliberately bad label design.

    A real metrics backend would create one time series for each distinct
    labelset.  Including job_id therefore makes series count scale with jobs.
    """

    return {
        (("job_id", event.job_id), ("outcome", event.outcome or "unknown"))
        for event in window.events
        if event.event == "finished"
    }


def lifecycle_events(window: ProductionWindow) -> Iterable[JobLifecycleEvent]:
    """Expose detailed events for diagnosis-oriented consumers."""

    return window.events
