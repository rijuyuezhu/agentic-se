# M10 Reviewer Brief

You are reviewing a proposed TaskForge change.

## Requested change

Prepare TaskForge for a future remote-worker design by **localizing lifecycle semantic authority behind one in-process boundary**.

This change is intended to be a **structural / architecture-enabling refactor only**.

For this PR:

- existing externally observable behavior should remain unchanged;
- current scheduling semantics should remain unchanged;
- current snapshot format and compatibility behavior should remain unchanged;
- the intentionally unsafe M07 `concurrent_claim.py` fault-injection artifact is **out of scope** and may continue to access raw state directly;
- do not add RPC, database, queue, or remote-worker mechanisms yet.

## Your responsibility

Review the candidate as an independent reviewer.

Do not assume the author/Agent description, tests, or risk assessment are correct merely because they are presented confidently.
