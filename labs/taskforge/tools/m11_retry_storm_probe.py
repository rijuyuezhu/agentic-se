from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Round:
    index: int
    new_requests: int
    retries: int
    attempts: int
    capacity: int
    completed: int
    timed_out: int


def run_naive_retry_storm(
    *, rounds: int = 6, new_requests_per_round: int = 8, capacity_per_round: int = 4
) -> tuple[Round, ...]:
    """Deterministic overload model for M11.

    Every timed-out attempt is retried in the next round. New demand continues
    to arrive while the dependency remains capacity-limited. This is a teaching
    model, not a wall-clock benchmark or a claim about TaskForge production
    throughput.
    """

    retries = 0
    history: list[Round] = []
    for index in range(rounds):
        attempts = new_requests_per_round + retries
        completed = min(attempts, capacity_per_round)
        timed_out = attempts - completed
        history.append(
            Round(
                index=index,
                new_requests=new_requests_per_round,
                retries=retries,
                attempts=attempts,
                capacity=capacity_per_round,
                completed=completed,
                timed_out=timed_out,
            )
        )
        retries = timed_out
    return tuple(history)


def run_retry_budget(
    *, rounds: int = 6, new_requests_per_round: int = 8, capacity_per_round: int = 4
) -> tuple[Round, ...]:
    """Comparison model with a bounded retry budget.

    At most one retry is admitted for every four new logical requests in a
    round. The exact policy is intentionally illustrative: M11 asks students to
    reason about amplification and action contracts, not to cargo-cult this
    ratio into production.
    """

    pending_retries = 0
    history: list[Round] = []
    retry_budget = new_requests_per_round // 4
    for index in range(rounds):
        admitted_retries = min(pending_retries, retry_budget)
        attempts = new_requests_per_round + admitted_retries
        completed = min(attempts, capacity_per_round)
        timed_out = attempts - completed
        history.append(
            Round(
                index=index,
                new_requests=new_requests_per_round,
                retries=admitted_retries,
                attempts=attempts,
                capacity=capacity_per_round,
                completed=completed,
                timed_out=timed_out,
            )
        )
        pending_retries = timed_out
    return tuple(history)


def _print(label: str, history: tuple[Round, ...]) -> None:
    print(label)
    print("round new retry attempts capacity completed timed_out")
    for row in history:
        print(
            f"{row.index:>5} {row.new_requests:>3} {row.retries:>5} "
            f"{row.attempts:>8} {row.capacity:>8} {row.completed:>9} {row.timed_out:>9}"
        )
    print(
        "totals "
        f"attempts={sum(row.attempts for row in history)} "
        f"completed={sum(row.completed for row in history)} "
        f"timed_out={sum(row.timed_out for row in history)}"
    )
    print()


def main() -> int:
    naive = run_naive_retry_storm()
    budgeted = run_retry_budget()

    naive_attempts = [row.attempts for row in naive]
    if naive_attempts != [8, 12, 16, 20, 24, 28]:
        raise AssertionError(f"retry-storm teaching baseline changed: {naive_attempts!r}")
    if [row.attempts for row in budgeted] != [8, 10, 10, 10, 10, 10]:
        raise AssertionError("retry-budget teaching baseline changed")

    _print("[NAIVE IMMEDIATE RETRY]", naive)
    _print("[BOUNDED RETRY BUDGET]", budgeted)
    print(
        "[INTERPRETATION] retries are load; under sustained overload, an unconstrained "
        "retry policy amplifies attempts instead of creating capacity"
    )
    print(
        "[LIMIT] this deterministic model demonstrates amplification only; it does not "
        "select a universal timeout, backoff, jitter, or retry-budget policy"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
