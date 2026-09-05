from __future__ import annotations

import threading

from taskforge import concurrent_claim, effect_delivery, service


def double_claim_probe() -> None:
    service.reset_for_tests()
    concurrent_claim.reset_for_tests()
    job_id = service.submit("echo race")

    barrier = threading.Barrier(2)
    receipts: list[concurrent_claim.ClaimReceipt] = []
    errors: list[BaseException] = []
    receipts_lock = threading.Lock()

    def after_observe(worker_id: str, observed_job_id: str) -> None:
        if observed_job_id != job_id:
            raise AssertionError(
                f"{worker_id}: expected to observe {job_id}, got {observed_job_id}"
            )
        barrier.wait(timeout=2)

    def run(worker_id: str) -> None:
        try:
            receipt = concurrent_claim.claim_next(
                worker_id,
                after_observe=after_observe,
            )
            if receipt is not None:
                with receipts_lock:
                    receipts.append(receipt)
        except BaseException as exc:  # preserve thread failures for the main thread
            with receipts_lock:
                errors.append(exc)

    threads = [
        threading.Thread(target=run, args=("worker-A",), daemon=True),
        threading.Thread(target=run, args=("worker-B",), daemon=True),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)

    if any(thread.is_alive() for thread in threads):
        raise AssertionError("double-claim probe deadlocked")
    if errors:
        raise AssertionError(f"worker thread failed: {errors!r}")

    successful_workers = sorted(receipt.worker_id for receipt in receipts)
    if successful_workers != ["worker-A", "worker-B"]:
        raise AssertionError(
            "starter was expected to demonstrate two successful claims; "
            f"got {successful_workers!r}"
        )

    owner = concurrent_claim.owner_of(job_id)
    if owner not in {"worker-A", "worker-B"}:
        raise AssertionError(f"unexpected final owner: {owner!r}")

    print(
        "[RACE REPRODUCED] one queued job produced two successful claims: "
        "worker-A, worker-B"
    )
    print("[FINAL STATE] one RUNNING job and one recorded owner can hide the bad history")


def crash_window_probe() -> None:
    effect_delivery.reset_for_tests()
    external_effects: list[str] = []

    def external_effect(job_id: str) -> None:
        external_effects.append(job_id)

    try:
        effect_delivery.deliver_once(
            "job-effect-1",
            external_effect,
            crash_after_effect=True,
        )
    except effect_delivery.SimulatedCrash:
        pass
    else:
        raise AssertionError("expected the explicit after-effect failpoint to fire")

    if external_effects != ["job-effect-1"]:
        raise AssertionError(f"unexpected first effect history: {external_effects!r}")
    if "job-effect-1" in effect_delivery.completed_jobs:
        raise AssertionError("completion bookkeeping should be missing after simulated crash")

    effect_delivery.deliver_once("job-effect-1", external_effect)

    if external_effects != ["job-effect-1", "job-effect-1"]:
        raise AssertionError(f"expected duplicate effect after retry: {external_effects!r}")

    print(
        "[CRASH REPRODUCED] effect happened, completion record was lost, "
        "retry produced a duplicate effect"
    )

    # Show why merely reversing the order trades duplication for loss.
    recorded_first: set[str] = set()
    effects_if_record_first: list[str] = []
    recorded_first.add("job-effect-2")
    # Simulated crash occurs here, before the external effect.
    if "job-effect-2" in recorded_first:
        # Recovery believes work is done and suppresses the retry.
        pass
    else:
        effects_if_record_first.append("job-effect-2")

    if effects_if_record_first:
        raise AssertionError("record-first demonstration should lose the external effect")

    print(
        "[ORDER REVERSAL] recording completion first avoids duplication but can lose the effect"
    )


def main() -> int:
    double_claim_probe()
    crash_window_probe()
    print("M07 deterministic interleaving/failure probe completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
