# M12 Editorial Review — Agentic Software Engineering rewrite

## 1. Batch scope

This batch rewrites M12 only, on base `77a44adf3ee2da7831cb9d20a2c8975f08f5134b` (`main` after the M11 rewrite). It does not change canonical TaskForge product behavior and must not be merged without independent review.

Changed teaching artifacts:

- `modules/12-agentic-software-engineering.md`
- `labs/12-agentic-software-engineering.md`
- `case-studies/m12/instructor-analysis.md`
- `reading-notes/m12-source-audit.md`
- `labs/taskforge/agent-contracts/m12/unsafe-agent-plan.json`
- `MATERIALS_REVIEW.md` (M12 source-ledger freshness only)
- this editorial record

The JSON fixture change is semantic repair for the teaching counterexample, not a new product feature.

## 2. Why M12 needed a full editorial rewrite

The merge-base M12 had substantial technical content but was organized as an answer-card encyclopedia rather than a sustained chapter:

```text
module: 2841 lines / 82 H1 / 197 text fences
Lab:    1155 lines / 32 H1 / 72 text fences
case:   1659 lines / 53 H1 / 131 text fences
```

A cold reader had to learn dozens of abstractions before the TaskForge case became the main explanatory engine. The Lab and instructor case repeated the same ideas in many small top-level sections.

The rewrite uses one change episode throughout:

```text
M11 false-green production evidence
    -> vague "add admission control" delegation
    -> real TaskForge reconnaissance
    -> engineered delegation contract
    -> unsafe authority drift
    -> bounded plan stops
    -> durable human decision
    -> authorized candidate + verification evidence
    -> separate review reasoning + adjudication
    -> parallelism / durable context / autonomy transfer
```

Concepts now appear because the case creates pressure for them.

## 3. Real baseline re-audited before writing

The rewrite was not based on old prose alone. Current canonical TaskForge was read directly:

- `public_api.submit_job()` is a shallow wrapper over `service.submit()`;
- `service.submit()` allocates `job-N`, increments `state.next_job_number`, and creates the authoritative `Job`;
- `metrics.queued_count()` is a projection over the same `state.jobs`;
- `worker.claim_next()` mutates the same lifecycle authority;
- there is no existing submit/admission lock;
- M11 production instrumentation is teaching-only and deterministic.

Executable baseline was reproduced:

```text
core pytest -> 6 passed

M11:
naive healthy=true
success_ratio=1.0
ending_queue_depth=0
good=2 bad=10 total=12 sli=0.167 target=0.990

M12:
vague      -> INSUFFICIENT_CONTRACT
engineered -> STRUCTURALLY_COMPLETE
unsafe     -> REJECT_PLAN
bounded    -> STOP_AND_ESCALATE
authorized -> AUTHORIZED_TO_IMPLEMENT
```

`m12_orchestration_probe.py` is treated as a structural teaching checker, not a semantic safety proof.

## 4. Canonical running-case contract

The engineered task already authorizes the broad direction: add an opt-in admission path while preserving legacy behavior. It does **not** authorize the implementation agent to invent the exact public overload result, product threshold, broader legacy migration, SLO rewrite, merge or deployment policy.

`M12-ADMISSION-001` then bounds the remaining feature decision:

- legacy `submit_job()` stays unchanged;
- opt-in admitted submit gets machine-readable accepted/overloaded results;
- threshold is supplied by caller/config owner and is a nonnegative integer;
- negative threshold fails before mutation;
- rejected admission creates no `Job` and consumes no id;
- admitted submissions serialize admission-check + creation against each other;
- legacy submit can bypass admission;
- worker claim may interleave and make an admission decision conservative/stale;
- the contract is **not** a global exact occupancy invariant.

The chapter marks this as a bounded teaching decision, not a universal admission architecture.

## 5. M11 denominator seam repaired

The merge-base M12 could be read as if rejected submissions inherently belonged in the M11 denominator and excluding them was automatically gaming. That is inconsistent with the rewritten M11 specification.

M11's start-latency SLI population is accepted jobs. A pre-acceptance admission rejection therefore does not naturally enter that accepted-job latency denominator. The protected rule is narrower:

```text
do not silently redefine the existing accepted-work population,
do not drop already-accepted slow work,
and do not reclassify rejection as accepted-work success.
```

If product owners care about admission rejection / availability, that requires a separate SLI specification or an explicit revised product contract.

The old unsafe fixture line:

```text
exclude rejected submissions from the SLI denominator
```

was replaced with a real violation:

```text
exclude already-accepted jobs whose claim latency exceeds the target
from the M11 SLI denominator
```

The executable M12 checker still rejects the plan as `change SLI denominator without authority`.

## 6. Cold-reader abstraction dependency sweep

The rewritten module introduces abstractions only after a concrete failure creates the need:

1. vague admission request creates unresolved decision space;
2. delegation contract appears as the remedy for hidden assumptions;
3. unsafe plan creates the need to distinguish capability / permission / authority;
4. bounded open questions create `STOP_AND_ESCALATE`;
5. human decision creates the authorized implementation scope;
6. real TaskForge call/state paths motivate read-broadly/write-narrowly;
7. candidate-controlled green tests create the evidence/oracle problem;
8. correlated self-certification creates the need for an independent acceptance path, while M10's verification/review distinction determines what kind of path it is;
9. reviewer configuration creates the trust-boundary discussion;
10. long-running state creates durable context / scoped instructions;
11. multiple review questions create multi-agent decomposition;
12. changing model capability creates harness simplification pressure;
13. conflicting productivity studies create local measurement pressure;
14. merge/deploy examples create the autonomy ladder.

The chapter no longer starts by asking the reader to memorize a long Agent vocabulary.

## 7. Design-decision dependency sweep

The rewrite checks that decisions are not presented as natural facts before their authority source appears.

- The broad opt-in direction comes from the engineered task.
- Exact overload shape, threshold ownership/domain, rejection side effects and admitted concurrency scope appear only after `M12-ADMISSION-001`.
- The instructor lock implementation appears only after the decision and is explicitly one implementation of that bounded contract.
- Legacy bypass is a declared non-guarantee, not a hidden defect.
- Stronger mandatory/global admission is deferred to a future compatibility/architecture decision.
- M11's accepted-job SLI specification remains its own measurement authority.
- Reviewer findings challenge the candidate but do not become new product specification automatically.
- Merge/deploy autonomy can be policy-authorized in mature bounded cases; human clicking is not treated as a permanent universal rule.

## 8. Authority and state-model sweep

The chapter keeps four layers separate:

```text
capability: can the Agent technically do it?
permission: does the execution environment allow it?
authority: may the Agent make this engineering decision?
evidence: what observed fact supports a completion claim?
```

Tool/sandbox policy can enforce or constrain allowed action surfaces, but tool permission does not itself grant semantic authority.

TaskForge state projections are also kept narrow:

- `state.jobs` / allocator are the canonical starter lifecycle state;
- queue depth is a derived projection, not a new authority;
- admission reference does not create a second job registry;
- rejection's no-id-consumption rule is Lab-specific, not a universal ID invariant;
- admitted-to-admitted serialization does not imply global linearizability across legacy submit + worker claim;
- M11 start-latency evidence measures accepted submission -> first authoritative claim, not admission availability.

## 9. Evidence / oracle preservation sweep

Merge-base technical intent retained:

- tests green is not enough if candidate can rewrite the evaluator;
- historical harness failure must be classified by semantic applicability, not mechanically preserved/deleted;
- concurrency stress alone is not atomicity proof;
- negative control + critical-section review + behavior test are complementary evidence;
- implementation summary is an index, not raw evidence;
- self-review is valuable but not independent acceptance;
- independent acceptance is the broad goal; independent verification and independent review remain distinct signals from M10;
- runtime probes, static checkers and external oracles can provide independent verification, but they do not themselves reconstruct a review change model;
- the canonical M12 Lab requires a separate Review Agent context/session after the Implementation Agent; using the same model in a fresh session is sufficient, and a different vendor is not required;
- reviewer itself has bounded authority and needs adjudication;
- Agent-generated tests are not discounted merely for being AI-generated, but oracle ownership must be inspected.

The Lab now asks for `claim -> evidence -> observed result -> scope/limitation`, rather than only a green command list.

## 10. Multi-agent and harness preservation sweep

The rewrite preserves the original curriculum without turning it into a vendor workflow:

- read-heavy independent questions are the preferred first parallelization exercise;
- the Lab reuses one guaranteed frozen pre-review candidate snapshot for three parallel Review Agent paths, instead of requiring a second candidate that the mandatory workflow never creates;
- the parallel comparison is now a deliverable/rubric proof obligation covering overlap, disagreement, wall-clock, synthesis cost and semantic-risk differences;
- write-heavy shared mutable surfaces receive more caution and remain an analysis exercise rather than a required multi-writer implementation;
- Git text conflict is only one form of conflict; semantic conflict can cross different files;
- task decomposition itself is engineering work;
- durable plans/progress reduce hidden context but cannot become a second product authority;
- stable repeated rules should migrate toward repo guidance, tests, CI/policy or runtime guardrails where appropriate;
- harness components encode assumptions that can become stale and should be simplified by evidence, not fashion;
- workflow vs agent is a control-structure choice, not a maturity hierarchy.

## 11. Productivity provenance sweep

The chapter does not pick a single AI productivity slogan.

It keeps three kinds of METR evidence separate:

- early-2025 RCT: a specific experienced-OSS setting observed about 19% slowdown despite perceived speedup;
- 2026 methodology update: wider adoption introduces strong selection effects that make a current task-level uplift estimate difficult to identify;
- 2026-05 self-report survey: 349 technical workers reported median value uplift measures around 1.4–2x and median speed change around 3x, with convenience-sample / selection / counterfactual-perception limitations.

The new May-2026 primary source was added to `m12-source-audit.md`. Course conclusion remains local measurement: cycle time, review/rework, quality, escaped defects, acceptance and human decision burden, not code/token/Agent count or subjective speed alone.

## 12. Current-product provenance boundaries

Current vendor/product facts were rechecked on 2026-09-07 and are kept explicitly time-sensitive:

- OpenAI Codex current guidance: `Goal / Context / Constraints / Done when`, scoped `AGENTS.md`, self-contained ExecPlans, subagent/read-heavy parallelism guidance, shell/MCP guardrail boundary;
- GitHub Copilot code review: current docs say repository custom instructions / agent instructions / skills are read from the PR head branch;
- Anthropic materials: workflow-vs-agent framing, long-running harness lessons, verifier/parallel-agent experiments;
- SWE-bench/METR: empirical evaluation/review/productivity evidence.

M12's expanded delegation-contract fields, Capability/Permission/Authority teaching split, authority ladder, `STOP_AND_ESCALATE` orchestration state and full TaskForge loop are course synthesis. They are not presented as OpenAI/Anthropic/GitHub standards.

## 13. Final executable validation

After the rewrite and fixture repair, the canonical TaskForge commands were re-run:

```text
core pytest: 6 passed
M04 boundary: baseline behavior reproduced
M05 dashboard: fingerprints unchanged
M06 legacy audit: fingerprints unchanged
M07: race/crash/order phenomena reproduced
M08: compatibility baseline reproduced
M09: architecture inventory reproduced
M11: naive healthy + 2/12 start-latency gap reproduced
M12: vague/unsafe/bounded/authorized decisions reproduced
```

The changed unsafe plan remains `REJECT_PLAN` for the intended reasons.

Editorial/hygiene checks:

```text
git diff --check: PASS
relative Markdown links: PASS
unsafe-agent-plan.json: JSON parse PASS

module: 299 lines / 1 H1 / 15 H2 / 2 text fences
Lab:    514 lines / 1 H1 / 21 H2 / 12 text fences
case:   258 lines / 1 H1 / 18 H2 / 4 text fences
```

Remaining `text` fences in the teaching artifacts are actual control-flow/output/evidence examples, not prose callout boxes.

## 14. Independent reviewer focus

A reviewer should independently check at least:

- whether the M11 false-green -> admission-delegation episode genuinely drives the whole module;
- whether vague-task pressure precedes delegation-contract abstraction;
- whether capability, permission and authority remain distinct;
- whether tool permission is prevented from becoming authority by implication;
- whether `STOP_AND_ESCALATE` is a real success state rather than ceremonial wording;
- whether `M12-ADMISSION-001` is neither under-read nor inflated into a final architecture;
- whether legacy bypass / worker interleaving / admitted-only serialization qualifiers stay visible;
- whether the accepted-job SLI denominator seam is now semantically correct across module, Lab, case, source audit and fixture;
- whether candidate-controlled oracle and historical-harness applicability are treated precisely;
- whether independent verification and independent review remain distinct rather than being collapsed under one reviewer label;
- whether the canonical Lab necessarily contains Implementation Agent -> separate Review Agent context -> human adjudication, without requiring a different model vendor;
- whether GitHub/OpenAI/Anthropic current-product claims remain clearly time-sensitive;
- whether METR study numbers retain their sample/method limitations;
- whether the parallel exercise has a guaranteed frozen input and a real deliverable/rubric proof obligation while avoiding a gratuitous write-heavy experiment;
- whether multi-agent parallelism is framed around decomposition and coordination cost, not Agent count;
- whether authority transfer/autonomy is risk- and policy-based rather than a permanent human-click requirement;
- whether the rewrite preserved the M13 bridge: implementation authority does not automatically become product-guarantee authority.

## 15. PR #17 review refinement — verification/review boundary and parallel input

The first independent review of PR #17 raised two diagnoses. Both were rechecked against `COURSE_DESIGN.md`, the M10 module, and the live M12 Lab before editing.

The first diagnosis was accepted: the rewrite had used `independent review` as an umbrella that also included runtime probes and static checkers. That erased M10's established `verification != review` distinction and made the canonical M12 assignment's second Review Agent optional in practice. The remediation was **not** to declare only humans or different model vendors to be independent. The broader engineering concept is now `independent acceptance path`; within it, verification evidence and review reasoning remain distinct. The Lab specifically requires a separate Review Agent context/session after the Implementation Agent, while allowing the same model in a fresh session. Human review remains legitimate in real engineering, but the human role in this exercise is adjudication; probes/checkers remain verification evidence rather than substitutes for the Review Agent.

The second diagnosis was also accepted: the old Phase 13 asked for an unreviewed candidate that the mandatory path did not guarantee, and the parallel exercise had no final proof obligation. The remediation deliberately does **not** restore the merge-base's optional write-heavy multi-agent coding experiment and does not invent a second implementation candidate. Phase 10 now freezes one complete pre-review candidate snapshot; Phase 11 reviews it; Phase 13 rewinds to the same snapshot and launches three read-only Review Agent paths without feeding them the earlier findings/adjudication. A compact `Parallel Review Comparison` is now required in deliverables and rubric.

## 16. PR #17 follow-up — temporal adjudication closure

A second independent review found one remaining temporal gap. The diagnosis was rechecked against the live Lab, module §10, and instructor analysis before editing: Phase 12 called its decision `final adjudication`, but Phase 13 intentionally generated fresh review findings afterward. That made it possible for a new blocker to appear after an earlier `ACCEPT` without a required authority path to close it.

The remediation keeps the teaching order intact. Phase 12 is now explicitly **first-pass adjudication** over the canonical Review Agent findings. Phase 13 still replays the same frozen pre-review candidate independently; however, every new material / contract-impacting finding must return to human adjudication, and any earlier `ACCEPT` remains provisional until those findings are closed. The Human Adjudication deliverable now covers both Phase 11 and Phase 13 material findings.

No module concept, TaskForge behavior, `M12-ADMISSION-001` semantic, M11 measurement definition, source claim, or rubric total changed in this follow-up.
