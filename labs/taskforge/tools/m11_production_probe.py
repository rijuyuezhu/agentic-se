from __future__ import annotations

from collections import defaultdict
import json

from taskforge.production_signals import (
    lifecycle_events,
    naive_health_summary,
    naive_metric_labelsets,
    run_deterministic_burst,
)


START_LATENCY_TARGET_S = 2.0
SLO_TARGET = 0.99


def _start_latency_by_job() -> tuple[dict[str, float], object]:
    window = run_deterministic_burst()
    submitted: dict[str, float] = {}
    claimed: dict[str, float] = {}
    for event in lifecycle_events(window):
        if event.event == "submitted":
            submitted[event.job_id] = event.at_s
        elif event.event == "claimed":
            claimed[event.job_id] = event.at_s

    latencies = {job_id: claimed[job_id] - at_s for job_id, at_s in submitted.items()}
    return latencies, window


def main() -> int:
    latencies, window = _start_latency_by_job()
    naive = naive_health_summary(window)

    good = sum(latency <= START_LATENCY_TARGET_S for latency in latencies.values())
    total = len(latencies)
    sli = good / total if total else 1.0
    bad = total - good

    labelsets = naive_metric_labelsets(window)
    event_ids = {event.job_id for event in lifecycle_events(window)}

    if naive != {
        "submitted": 12,
        "success_ratio": 1.0,
        "ending_queue_depth": 0,
        "healthy": True,
    }:
        raise AssertionError(f"M11 naive-health baseline changed: {naive!r}")
    if (good, bad, total) != (2, 10, 12):
        raise AssertionError(
            f"M11 user-centered SLI baseline changed: good={good} bad={bad} total={total}"
        )
    if len(labelsets) != 12:
        raise AssertionError(f"expected one metric series per job, got {len(labelsets)}")
    if len(event_ids) != 12:
        raise AssertionError("diagnostic event correlation baseline changed")

    print("[NAIVE DASHBOARD]")
    print(json.dumps(naive, indent=2, sort_keys=True))
    print()
    print("[USER-CENTERED START-LATENCY SLI]")
    print(f"good={good} bad={bad} total={total} sli={sli:.3f} target={SLO_TARGET:.3f}")
    print(
        "result=VIOLATED despite 100% eventual success and an empty ending queue"
        if sli < SLO_TARGET
        else "result=MET"
    )
    print()
    print("[MEASUREMENT BLIND SPOT]")
    print("ending queue depth is a point-in-time cause signal; it erased the wait experienced earlier")
    print()
    print("[CARDINALITY TRAP]")
    print(f"12 completed jobs -> {len(labelsets)} metric series because job_id is a label")
    print("job_id remains useful in lifecycle events/logs for correlation; signal shape matters")
    print()
    print("M11 production observability gap reproduced deterministically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
