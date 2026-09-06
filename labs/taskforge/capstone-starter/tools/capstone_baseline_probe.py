from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading

from taskforge_capstone import api, db, maintenance, remote_worker, service


def _database(root: Path, name: str) -> Path:
    path = root / name
    db.initialize(path)
    return path


def _reproduce_double_claim(root: Path) -> tuple[list[dict[str, object] | None], dict[str, object]]:
    path = _database(root, "claim-race.db")
    job_id = service.submit(path, "echo race", created_at=1.0)
    observed = threading.Barrier(2)

    def after_observe(_: str) -> None:
        observed.wait()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(remote_worker.claim_next, path, "worker-a", after_observe=after_observe)
        b = pool.submit(remote_worker.claim_next, path, "worker-b", after_observe=after_observe)
        claims = [a.result(), b.result()]

    return claims, service.get(path, job_id)


def _reproduce_stale_finish(root: Path) -> dict[str, object]:
    path = _database(root, "stale-finish.db")
    job_id = service.submit(path, "charge-card", created_at=1.0)

    first_claim = remote_worker.claim_next(path, "worker-a")
    assert first_claim is not None
    assert maintenance.operator_requeue(path, job_id) is True
    second_claim = remote_worker.claim_next(path, "worker-b")
    assert second_claim is not None

    stale_payload = {"job_id": job_id, "exit_code": 0}
    stale_accepted = remote_worker.finish_job(path, stale_payload)

    return {
        "first_claim": first_claim,
        "second_claim": second_claim,
        "stale_finish_accepted": stale_accepted,
        "final_job": service.get(path, job_id),
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="taskforge-capstone-") as tmp:
        root = Path(tmp)

        path = _database(root, "baseline.db")
        legacy = api.submit_job(path, "echo legacy", now=100.0)
        print("[LEGACY PUBLIC CONTRACT]")
        print(json.dumps(legacy, sort_keys=True))
        print()

        print("[DURABLE SCHEMA]")
        print(f"user_version={db.schema_version(path)}")
        print("columns=" + ",".join(db.job_columns(path)))
        print()

        claims, final_job = _reproduce_double_claim(root)
        successful = [claim for claim in claims if claim is not None]
        print("[KNOWN REMOTE CLAIM RACE]")
        print("successful_claims=" + ",".join(sorted(str(claim["job_id"]) for claim in successful)))
        print("workers_returned_success=" + str(len(successful)))
        print(
            "final_row_has_single_owner="
            + str(final_job["worker_id"] in {"worker-a", "worker-b"}).lower()
        )
        print("history_is_illegal=" + str(len(successful) == 2).lower())
        print()

        stale = _reproduce_stale_finish(root)
        print("[HISTORICAL COMPLETION QUIRK]")
        print("legacy_finish_fields=job_id,exit_code")
        print("first_worker=" + str(stale["first_claim"]))
        print("second_worker=" + str(stale["second_claim"]))
        print("stale_finish_accepted=" + str(stale["stale_finish_accepted"]).lower())
        print("final_status=" + str(stale["final_job"]["status"]))
        print("final_worker_id=" + str(stale["final_job"]["worker_id"]))
        print()

        print("[CAPSTONE PRESSURE]")
        print("automatic lease expiry + requeue cannot identify a stale v1 completion")
        print("exactly-once external execution is not implied by state fencing")
        print("mixed-version rollout therefore needs an explicit compatibility window and gate")
        print()
        print("TaskForge capstone baseline reproduced deterministically")


if __name__ == "__main__":
    main()
