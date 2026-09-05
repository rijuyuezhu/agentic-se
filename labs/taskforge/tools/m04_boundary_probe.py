from __future__ import annotations

from taskforge import public_api, service, worker


def show(label: str, thunk) -> None:
    try:
        value = thunk()
    except Exception as exc:  # deliberately observing the current public surface
        print(f"{label}: EXCEPTION {type(exc).__name__}: {exc}")
    else:
        print(f"{label}: {value!r}")


def main() -> None:
    service.reset_for_tests()

    show("blank submit", lambda: public_api.submit_job("   "))

    service.reset_for_tests()
    show("unknown get", lambda: public_api.get_job("job-404"))
    show("unknown cancel", lambda: public_api.cancel_job("job-404"))

    service.reset_for_tests()
    running = public_api.submit_job("sleep 10")["job_id"]
    worker.claim_next()
    show("cancel running", lambda: public_api.cancel_job(running))

    service.reset_for_tests()
    finished = public_api.submit_job("true")["job_id"]
    worker.claim_next()
    worker.finish(finished, 0)
    show("cancel succeeded", lambda: public_api.cancel_job(finished))

    service.reset_for_tests()
    first = public_api.submit_job("echo same")["job_id"]
    second = public_api.submit_job("echo same")["job_id"]
    print(f"same payload twice: first={first!r}, second={second!r}")

    print("jobs:", [job["id"] for job in public_api.list_jobs()])


if __name__ == "__main__":
    main()
