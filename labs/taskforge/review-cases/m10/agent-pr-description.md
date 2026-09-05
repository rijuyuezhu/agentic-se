# Candidate PR: centralize TaskForge lifecycle authority

> **Review case. Do not assume the claims below are true.** This is the author/Agent supplied PR description.

## Problem

M09 found lifecycle mutations spread across `service.py` and `worker.py`, while metrics and the legacy audit also know the storage representation. This makes it harder to evolve TaskForge toward a remote-worker architecture.

## Change

- add `JobAuthority` as the single owner of lifecycle state;
- route service, worker, metrics, and legacy audit through it;
- preserve all current behavior;
- use stable job-id ordering so readers and workers see deterministic ordering;
- treat cancelling an unknown job like any other non-cancellable job and return `False`;
- add focused authority tests.

## Risk

Low. This is an internal refactor: no public API, snapshot format, or lifecycle behavior changes are intended.

## Evidence

```text
9 passed
```

All TaskForge pytest tests pass locally.

## Follow-up

A later PR can put an RPC transport in front of `JobAuthority` for remote workers.
