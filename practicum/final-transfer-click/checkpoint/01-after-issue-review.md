---
id: practicum-click-checkpoint-01
type: practicum
visibility: student
related: [practicum-click]
---
# Maintainer Reply — only read after first-pass issue review is frozen

> **Stop.** Before reading this file, your `Reconnaissance Record`、`Issue Review` 和 first-pass `Design Memo` must already be committed in your practicum workspace. Do not rewrite that first-pass artifact after seeing this decision; append an addendum instead.

Thanks for challenging the request rather than implementing the suggested `filesystem_root` literally.

We are changing the product decision:

- **Do not promise same-process concurrent `CliRunner` safety in the 8.x line.** Click's test helpers may continue to mutate interpreter-global process state; callers that need true parallel isolation should use process isolation or another test-framework mechanism.
- Keep the current `CliRunner.isolated_filesystem()` API source-compatible for 8.x, but **deprecate it**. Removal, if any, is a future major-version decision.
- Preserve its current non-concurrent behavior during the compatibility window.
- Update testing documentation so new code prefers caller/test-framework-owned temporary directories; for pytest, show `tmp_path` as the normal path.
- Make the relevant thread-safety/process-global limitation explicit. Do not imply that replacing only filesystem isolation makes the rest of `CliRunner` thread-safe.
- Migrate Click's own tests away from `isolated_filesystem()` where this is local and does not change the behavior under test.
- Do not add a global lock, virtual filesystem abstraction, subprocess runner, or new public filesystem API as part of this change.
- Add focused deprecation evidence and update release/upgrade documentation according to this repository's conventions.

This decision authorizes a compatibility/deprecation change. It does **not** authorize unrelated cleanup or a broader redesign of Click's testing machinery.
