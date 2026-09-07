# M11 Editorial Review — Production / Observability / Reliability rewrite

## 1. Batch scope

This batch rewrites M11 only. Base is `main` after PR #15 (`01f02edfec38dfffbc73414802dfea789e395765`). M12 remains out of scope except for a short bridge about future Agent tool/action authority.

Changed teaching artifacts:

- `modules/11-production-observability-reliability.md`
- `labs/11-production-observability-reliability.md`
- `case-studies/m11/instructor-analysis.md`
- `reading-notes/m11-source-audit.md`
- new `reading-notes/m11-editorial-review.md`
- new teaching-only probe `labs/taskforge/tools/m11_retry_storm_probe.py`

No canonical TaskForge lifecycle/product behavior is changed. The new retry-storm probe is a deterministic failure model, not a production feature or throughput benchmark.

## 2. Why M11 remains a separate batch

`COURSE_DESIGN.md` gives M11 a coherent production-engineering authority:

```text
logs / metrics / traces as evidence
SLO intuition
overload
backoff
incident
postmortem
operational simplicity
```

M12 is materially different: context engineering, task decomposition, Agent boundary, tool authority, verification, independent review, parallel agents and merge conflicts. Mixing them would blur operational evidence authority with Agent orchestration authority.

## 3. Merge-base problem

Merge-base M11 had strong technical content but was structurally atomized:

```text
module: 3278 lines / 112 top-level H1 sections
Lab:     889 lines / 32 top-level H1 sections
case:    810 lines / 26 top-level H1 sections
```

The module read like a long answer-card/index of observability concepts. Many claims were individually good, but a cold reader had to remember why each concept mattered and repeatedly reconstruct the same TaskForge scenario.

The rewrite chooses one running contradiction:

```text
all jobs eventually succeed
ending queue depth = 0
naive dashboard = healthy
BUT
only 2/12 accepted jobs start within 2s
```

That single history now drives SLI specification, measurement placement, denominator/missingness, signal shape, SLO/error budget, alert action contract, overload/backpressure and rollout.

A second failure episode is then added:

```text
overload
+ immediate retries
-> retry attempts become new load
-> amplification / incident
-> mitigation
-> postmortem / learning
```

This lets incident/postmortem emerge from an already understood system state instead of appearing as a late vocabulary card.

## 4. Real baseline evidence

Current starter facts remain:

- `production_signals.py` is teaching-only in-process instrumentation;
- `run_deterministic_burst()` uses synthetic timestamps, not wall clock;
- 12 jobs are submitted first and processed sequentially by one worker;
- every job eventually succeeds;
- ending queue depth is 0;
- naive summary reports healthy;
- authoritative submit→claim SLI has 2 good / 10 bad / 12 total at the teaching 2s target;
- naive metric labelsets create one distinct series identity per completed job because `job_id` is a label;
- lifecycle events preserve `job_id` for diagnosis/correlation.

These facts are not rewritten into claims about real TaskForge production throughput.

## 5. Curriculum gap discovered during rewrite: retry/backoff was named but not executable

`COURSE_DESIGN.md` explicitly requires injecting a timeout/retry storm. Merge-base M11 discussed retries/backpressure but the Lab did not provide a deterministic failure injection that a student could run.

The new `m11_retry_storm_probe.py` fills that gap without altering TaskForge product semantics.

Teaching model:

```text
new logical demand per round = 8
downstream capacity per round = 4
naive: every timed-out attempt retries next round
```

Expected attempts:

```text
8, 12, 16, 20, 24, 28
```

A comparison with a bounded retry budget yields:

```text
8, 10, 10, 10, 10, 10
```

The probe proves only the failure shape: retries consume capacity and can amplify sustained overload. It does **not** choose a universal timeout, retry count, backoff base, jitter algorithm or retry-budget ratio.

M04/M07 qualifiers are kept explicit:

- timeout does not prove non-execution;
- backoff/jitter does not produce exactly-once;
- retry budget does not create capacity;
- non-idempotent effects still need identity/dedup semantics.

## 6. Curriculum gap discovered during rewrite: postmortem had no audited primary authority

`COURSE_DESIGN.md` requires a blameless but technically precise postmortem. Merge-base module contained a postmortem section, but the source audit had no dedicated primary source for that claim cluster.

This batch audited and added Google SRE primary material:

- `https://sre.google/sre-book/postmortem-culture/`
- `https://sre.google/workbook/postmortem-culture/`

Source-backed points used in M11:

- postmortem records incident impact, response/mitigation, causes and follow-up actions;
- blamelessness focuses on system/process conditions rather than blame;
- action items should have verifiable completion and prevention/mitigation value;
- incident learning should feed detection, mitigation, coordination, process and system changes;
- writing the document is not enough if action items never close.

Course adaptation remains explicit: M11 asks students to connect overload/retry amplification, detection gaps and operational evidence to a TaskForge teaching incident. It does not claim Google’s exact process/template is mandatory.

## 7. Source audit completion for retry amplification

This batch also added primary Google SRE sources for retry amplification/backoff:

- `https://sre.google/sre-book/addressing-cascading-failures/`
- `https://sre.google/sre-book/service-best-practices/`

Source-backed claims are kept bounded:

- retries can amplify overload;
- randomized exponential backoff is an important mitigation pattern;
- load shedding / traffic reduction / graceful degradation can help under overload;
- concrete retry/timeout parameters depend on service context.

Course synthesis is the discrete retry-storm probe and the phrase “retry is load”. The probe’s fixed ratios are not source-backed production recommendations.

### Post-review closure: canonical signal-selection transfer

Independent review correctly identified a different compression loss: the rewritten running case taught latency/missingness well, but `COURSE_DESIGN.md` also requires `logs / metrics / traces as evidence` and an assignment that distinguishes **slow / hung-or-no-progress / data-inconsistent** behavior.

This was not fixed by restoring old telemetry encyclopedia sections. The artifact chain now adds one bounded transfer exercise:

```text
failure question
-> signal shape
-> evidence limitation
```

- slow: user latency aggregate + cause metrics; trace only if cross-component path/timing is the question;
- no progress: lifecycle/oldest-age/heartbeat-or-equivalent progress evidence, while missing telemetry remains ambiguous;
- inconsistent data: first define which authority/read surfaces should agree and under what freshness/consistency boundary, then use mismatch aggregation + identity/version/source diagnostic evidence; trace can localize a cross-service serving/replication path but cannot establish authority or correctness by itself.

The Lab now makes this `failure-signal-matrix.md` a deliverable and rubric obligation. No tracing SDK or new executable probe is required.

The source audit also adds the current OpenTelemetry Signals overview as primary calibration: metric = runtime measurement, log = event record, trace = request/path through components. This supports the signal-shape distinction without turning OTel into a required stack or a three-pillars definition.

### Post-review provenance closure: operational simplicity

Independent review also correctly noted that the module had promoted operational simplicity into a strong M11 claim while the audit did not yet have dedicated primary provenance.

Added Google SRE primary material:

- `https://sre.google/sre-book/simplicity/`
- `https://sre.google/workbook/simplicity/`

The adopted claim stays bounded: end-to-end complexity in software, architecture, tools and lifecycle processes increases the surface that must be understood, tested, changed and operated, so simplicity is a reliability review dimension. Explicit non-claims remain: fewer tools/components are not automatically more reliable; LOC/service count/panel count are not reliability metrics; necessary redundancy/isolation/telemetry is not rejected merely for adding components.

## 8. Semantic preservation sweep

The rewrite explicitly preserves these merge-base claims/qualifiers:

### User-centered SLI

- user/product expectation precedes convenient existing metrics;
- SLI specification != SLI implementation;
- measurement placement changes blind spots;
- good/total is useful but not the only possible SLI form;
- 99%/2s is a teaching target, not a universal best practice.

### Denominator / missingness

- accepted-but-unobserved work cannot silently disappear;
- unknown/pending policy is contract-specific;
- telemetry coverage gaps may deserve their own evidence;
- unknown is not automatically good.

### Signal shape / cardinality

- `job_id` can be useful diagnostic correlation while being inappropriate as aggregate metric label;
- behavior-level cardinality negative control is preferred over source-string grep;
- high-cardinality metrics are not declared universally forbidden; the cost model matters;
- metric / event-log / trace are not collapsed into one diagnosis bucket: aggregate measurement, local event record and cross-component path evidence answer different questions;
- slow / no-progress / inconsistent-data transfer is now a Lab obligation, not a passing qualifier;
- trace is conditional on cross-component path/timing need and does not establish authority/correctness by itself.

### Telemetry compatibility/security

- event/metric schema can become a compatibility surface;
- M08-style migration may be needed when consumers exist;
- command/token/arbitrary user content is not default telemetry payload;
- retention/privacy/cost are part of design.

### Alert/action semantics

- page should connect to urgency and operator action;
- cause signals are usually diagnostic context, but cause-based paging can be valid when imminent impact/action is clear;
- ticket/page/logging are different action contracts;
- fixed burn-rate thresholds are not universal rules.

### Reliability mechanisms

- queue age can be more user-relevant than queue depth depending on workload;
- backpressure is propagation of capacity information, not a specific queue API;
- load shedding/degradation are product-semantic choices, not universal wins;
- retry/failover/fallback can themselves cause incidents.

### Rollout / evidence

- rollout signal must test the change hypothesis;
- feature flag is not rollback proof;
- simulation/failure injection/load test are evidence, not production truth;
- production evidence complements, not replaces, pre-production evidence.

### Incident/postmortem

- incident response may begin before root cause is known;
- correlation is not automatically causation;
- blameless does not mean vague;
- “operator error” is not a sufficient technical root cause;
- follow-up actions require verifiable closure.

## 9. Cold-reader dependency sweep

Abstractions now appear after pressure:

1. false-green dashboard establishes that observed signals answer the wrong question;
2. user journey creates need for SLI;
3. SLI creates need to separate specification from measurement implementation;
4. missing events create denominator/missingness pressure;
5. job-ID series explosion creates aggregate-vs-correlation signal-shape distinction;
6. slow / no-progress / inconsistent-data transfer forces metric/event-log/trace choice to follow the failure question;
7. consumer break creates telemetry compatibility;
8. “how good is good enough?” introduces SLO/budget;
9. “when must a human act?” introduces action-contract alerting;
10. sustained overload introduces backpressure/load shedding;
11. retries make recovery mechanism itself part of failure load;
12. the combined failure produces incident/postmortem reasoning.

The chapter no longer introduces postmortem or retry/backoff as detached encyclopedia entries.

## 10. Design-authority sweep

The rewrite avoids turning reference choices into universal architecture:

- service/worker event pair is one reference measurement implementation;
- `StartLatencySummary` is an instructor reference type, not canonical product API;
- bounded retry budget is a comparison model, not production policy;
- `production_observability.py` is a suggested Lab seam, not required architecture;
- Prometheus/Grafana/OTel and a tracing SDK are not required;
- heartbeat/lease is only one possible no-progress evidence mechanism, not a newly mandated TaskForge architecture;
- the derived read-model inconsistency case is an explicit future transfer case, not a claim that the starter currently has a replicated read model;
- canary percentages are not fixed;
- SLO targets are not copied from Google;
- overload responses are compared, not ranked universally.

## 11. State/model projection sweep

M11 projections are explicitly scoped:

- start-latency SLI models only accepted→first-claim, not complete TaskForge reliability;
- naive dashboard is a valid projection of eventual success/final queue, just insufficient for user history;
- queue depth is a point-in-time state projection, not full waiting history;
- diagnostic event identity is not aggregate metric identity;
- the inconsistent-data transfer only applies after declaring which surfaces/invariant should agree and under what freshness/consistency boundary;
- trace path evidence can localize where a value/request traveled but does not decide semantic authority;
- retry-storm discrete rounds model amplification, not wall-clock system capacity;
- incident evidence packet is a reasoning projection, not automatic root-cause proof.

## 12. Temporal consistency sweep

The rewrite keeps these time semantics aligned:

- accepted submission anchors SLI cohort;
- first authoritative claim is the measured completion of the start-latency phase;
- window-open work may be pending; window-close missing evidence follows explicit policy;
- final success does not retroactively erase prior latency violation;
- timeout/retry does not prove the first attempt did not execute;
- incident timeline distinguishes impact start, detection, mitigation and recovery;
- postmortem occurs after incident response but feeds future contract/design/test/operation work.

## 13. M12 leakage boundary

M11 still contains Agent-specific instrumentation/review material because `COURSE_DESIGN.md` expects Agent-era use. But it does not teach M12’s orchestration stack.

M11 claim:

```text
Agent can collect/generate/analyze production evidence,
but acceptable-service and production-action authority remain explicit.
```

Deferred to M12:

- context engineering for code;
- task decomposition;
- tool authority model;
- parallel implementer/reviewer agents;
- merge conflict handling;
- systematic independent-agent workflow design.

Independent review also surfaced one downstream wording seam that is intentionally **not** repaired in PR #16: current M12 sometimes treats `M11 denominator = accepted jobs` as a permanently protected authority and describes removing rejected work from a denominator as inherently goal gaming. M11’s narrower rule is different: the population of a particular SLI comes from its declared specification. Silently changing an already-declared population to make a result green is gaming; whether rejected submissions belong in a different/new availability or admission SLI is itself a specification question. M12 should reconcile that distinction during its own rewrite.

## 14. Final validation evidence

Executable gates were re-run after the rewrite:

```text
core pytest
=> 6 passed

M11 production probe
=> naive healthy=true
=> good=2 bad=10 total=12 sli=0.167
=> 12 jobs -> 12 naive job_id metric series

M11 retry-storm probe
=> naive attempts = 8, 12, 16, 20, 24, 28
=> bounded-budget attempts = 8, 10, 10, 10, 10, 10
=> probe explicitly states it does not choose production retry/backoff policy

M09 architecture inventory
=> unchanged baseline inventory

M10 author/reviewer case
=> author CI 9 passed
=> ordering/fifo/public-behavior/snapshot-order reviewer symptoms unchanged

M05/M06 fingerprints
=> unchanged

M07
=> race / crash / ordering teaching phenomena reproduced

M08
=> compatibility baseline unchanged
=> historical fixture sha256 = 0cd8f674d54b3da7919c2a9f7b911fdea5b109399438595c471a6baee90d2ecc
```

Hygiene / structure after rewrite:

```text
git diff --check = PASS
relative Markdown links = PASS
changed Markdown fences = balanced
module = 337 lines / 1 H1 / 18 H2 / 0 page separators
Lab = 561 lines / 1 H1 / 20 H2 / 0 page separators
instructor case = 313 lines / 1 H1 / 16 H2 / 0 page separators
source audit = 647 lines; primary/source sections 1-12 plus synthesis sections 13-16
editorial review = 405 lines / 1 H1 / 15 H2 / 0 separators
no uv.lock
```

Secret scan = no findings. Final staged scope = exactly five M11 Markdown artifacts; M12, canonical TaskForge product source, and `m11_retry_storm_probe.py` are unchanged in this follow-up.

## 15. Independent reviewer focus

This record is not self-approval. A reviewer should independently check at least:

- whether the false-green TaskForge case genuinely drives the chapter rather than merely decorating it;
- whether the 2s/99% teaching target is still clearly non-authoritative;
- whether accepted/claim/missingness temporal semantics remain coherent;
- whether slow / no-progress / inconsistent-data actually forms a signal-selection transfer obligation rather than another glossary table;
- whether metrics, event/log records and traces carry distinct evidence roles without making tracing mandatory;
- whether the inconsistency transfer declares the authority/read surfaces and freshness/consistency boundary before calling a mismatch a bug;
- whether trace/correlation is prevented from becoming correctness or authority proof;
- whether `job_id` metric-vs-event reasoning preserves correlation value without high-cardinality cargo cult;
- whether telemetry schema migration imports M08 precisely rather than making all logs permanent APIs;
- whether cause-based alert exceptions remain visible;
- whether retry-storm probe proves only amplification and does not invent production throughput/backoff policy;
- whether timeout/non-execution and duplicate-effect qualifiers remain consistent with M04/M07;
- whether overload alternatives remain real alternatives;
- whether postmortem is blameless **and** technically precise, with verifiable actions;
- whether operational simplicity has primary provenance while remaining a bounded tradeoff rather than “fewer tools/components is always better”;
- whether the M12 denominator seam is only recorded/deferred, not silently changed in this batch;
- whether M12 orchestration material has not leaked backward.
