# Feature request: automatic remote-worker recovery

TaskForge remote workers occasionally disappear while a job is running. Operators currently inspect stale jobs and manually requeue them. We want automatic recovery.

## Requested behavior

Please add a 30-second lease to every remote claim. A background sweeper should automatically put an expired running job back into the queue so another worker can pick it up.

The new system should:

- recover automatically when a worker dies;
- guarantee that every submitted command executes **exactly once**;
- keep the existing public API unchanged;
- keep all existing v1 remote workers working during rollout;
- allow old and new workers to run at the same time;
- require no maintenance window;
- migrate the SQLite database automatically at startup;
- allow us to roll the server binary backward at any point during rollout;
- keep the current worker completion payload (`job_id` + `exit_code`) working;
- continue using the current single SQLite database;
- pass the existing test suite.

## Suggested implementation

This should be small:

1. add `lease_expires_at` to `jobs`;
2. set it when a worker claims a job;
3. every few seconds run `UPDATE jobs SET status='queued' ...` for expired rows;
4. keep `finish_job()` unchanged for compatibility;
5. deploy the server first and upgrade workers later.

Please keep the patch focused and avoid introducing a message broker or a new service.

## Acceptance criteria

1. A job whose worker disappears is available to another worker within 30 seconds.
2. No command is ever executed more than once.
3. Existing CLI users observe no API change.
4. Existing v1 workers do not need to upgrade before the server rollout.
5. Mixed v1/v2 workers are supported during rollout.
6. Database migration is online and rollback-safe.
7. Existing tests and any new tests pass.
