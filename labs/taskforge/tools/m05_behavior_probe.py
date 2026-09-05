from __future__ import annotations

import hashlib

from taskforge import dashboard, service, worker


EXPECTED: dict[str, str] = {
    "empty": """TaskForge Dashboard
total=0 active=0 terminal=0
queued=0 running=0 succeeded=0 failed=0 cancelled=0
jobs:
<none>""",
    "queued": """Queue View
total=2 active=2 terminal=0
queued=2 running=0 succeeded=0 failed=0 cancelled=0
jobs:
job-1 | queued | echo first
job-2 | queued | echo second""",
    "mixed": """TaskForge Dashboard
total=5 active=2 terminal=3
queued=1 running=1 succeeded=1 failed=1 cancelled=1
jobs:
job-1 | succeeded(0) | true
job-2 | failed(7) | false
job-3 | cancelled | sleep cancelled
job-4 | running | sleep running
job-5 | queued | echo queued""",
}


def _empty() -> str:
    service.reset_for_tests()
    return dashboard.render_dashboard()


def _queued() -> str:
    service.reset_for_tests()
    service.submit("echo first")
    service.submit("echo second")
    return dashboard.render_dashboard("Queue View")


def _mixed() -> str:
    service.reset_for_tests()

    succeeded = service.submit("true")
    worker.claim_next()
    worker.finish(succeeded, 0)

    failed = service.submit("false")
    worker.claim_next()
    worker.finish(failed, 7)

    cancelled = service.submit("sleep cancelled")
    assert service.cancel(cancelled) is True

    service.submit("sleep running")
    worker.claim_next()

    service.submit("echo queued")

    return dashboard.render_dashboard()


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    actual = {
        "empty": _empty(),
        "queued": _queued(),
        "mixed": _mixed(),
    }

    failed = False
    for name, text in actual.items():
        expected = EXPECTED[name]
        if text != expected:
            failed = True
            print(f"[DRIFT] {name}")
            print("--- expected ---")
            print(expected)
            print("--- actual ---")
            print(text)
        else:
            print(f"[OK] {name}: sha256={_fingerprint(text)}")

    if failed:
        print("dashboard behavior drift detected")
        return 1

    print("all existing text dashboard behavior preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
