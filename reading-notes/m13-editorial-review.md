# M13 Editorial Review — Capstone rewrite

## 1. Batch scope and base

This rewrite starts from `main` commit `a8f688a48883a2a69f75737d85518f417702b406`, immediately after the accepted M12 rewrite was squash-merged.

Scope:

- `modules/13-capstone-change-engineering.md`
- `labs/13-capstone.md`
- `case-studies/m13/instructor-analysis.md`
- one provenance clarification in `reading-notes/m13-source-audit.md`

No TaskForge starter production code, fixture, decision pack, or baseline probe was changed.

Before editing, the following were re-read or executed: `COURSE_DESIGN.md`, `AGENT.md`, `EDITORIAL_GUIDE.md`, the complete M13 source audit, current module/Lab/instructor case, `capstone-starter/ISSUE.md`, human decision pack, all capstone starter source files, baseline tests and deterministic probe. The module file history was also checked; the current pre-rewrite M13 content originates from the original `course: add M13 capstone` commit rather than a prior editorial rewrite.

## 2. Actual starter baseline

The canonical starter was executed before prose changes:

```text
pytest: 6 passed

KNOWN REMOTE CLAIM RACE
successful_claims=job-1,job-1
workers_returned_success=2
final_row_has_single_owner=true
history_is_illegal=true

HISTORICAL COMPLETION QUIRK
stale_finish_accepted=true
final_status=succeeded
final_worker_id=worker-b
```

The baseline establishes the running pressure for the chapter: green characterization tests coexist with an illegal concurrent claim history and a stale completion path that can write terminal state after operator requeue/reclaim.

## 3. Main editorial diagnosis

The old M13 contained most of the right technical material, but its 1683-line module was structured like a detailed reference/checklist rather than a cold-reader narrative. More importantly, it had a design-decision dependency leak.

Before the section titled `Staged Reveal`, the old module already said that the system **needs attempt identity**, defined the “real lease contract,” and presented attempt fencing as the answer. Those are plausible and, after D1–D7, correct teaching decisions. But the Capstone Lab deliberately requires students to perform an independent issue review before reading the human decision pack. Revealing D3/D5-style decisions before that boundary weakens the very authority exercise the chapter is meant to test.

The rewrite therefore separates two kinds of pre-decision conclusion:

- conclusions that follow from observed code/evidence and can be stated before authority transfer: the original issue is internally inconsistent; old completion cannot distinguish stale execution; TaskForge cannot infer arbitrary external-effect exactly-once from its local DB;
- specific product/system decisions that must wait for the human decision reveal: `manual` legacy recovery, opt-in `automatic_at_least_once`, monotonic attempt identity, dual-protocol fencing, activation gate, and narrowed old-binary rollback guarantee.

This is the same design-decision dependency rule established by earlier editorial reviews: diagnosis may precede authority; the selected normative contract may not.

## 4. New running-example structure

The rewritten module now follows one continuous pressure chain:

```text
green baseline
  -> deterministic double-claim history
  -> stale v1 completion after requeue
  -> issue exactly-once / rollback contradiction
  -> STOP_AND_ESCALATE
  -> freeze independent issue review
  -> human authority decision
  -> attempt/fencing model
  -> state fencing != external effect exactly-once
  -> staged migration + rollback boundary
  -> existing-race-first change topology
  -> bounded Agent delegation
  -> evidence matrix + independent review
  -> production gate + final change record
```

The same TaskForge change drives the abstractions; message broker, SQLite transaction, disable-retry, and alternate schema shapes are transfer/rejected-path tests rather than separate mini-lectures.

## 5. Semantic preservation map

Important merge-base claims retained:

- M13 introduces composition, not a new normative SE theory.
- Existing system contracts and accidental behavior must be distinguished from requested behavior.
- Final DB state does not prove legal concurrent history.
- Baseline v1 claim has a deterministic double-success race.
- Historical v1 finish payload is `job_id + exit_code` and cannot fence a stale execution.
- Automatic retry for arbitrary external commands cannot by itself prove exactly-once external effects.
- Human decision D1–D7 remains the normative Capstone contract.
- Legacy submit response remains unchanged and defaults to manual recovery.
- `automatic_at_least_once` is explicit opt-in.
- New protocol has current-attempt fencing; legacy completion can only complete legacy attempt.
- Existing v1 claim race must be fixed before mixed rollout.
- Reference representation defaults (`attempt=0`, nullable lease, `manual`) retain their migration-specific qualifiers and are not presented as universal schema rules.
- CAS / conditional update is a reference implementation choice, not the contract; transaction or other equivalent atomic decision remains possible.
- State fencing and external-effect dedup/fencing remain separate authorities.
- External duplicate effect remains a mandatory negative control, not an implementation failure to hide.
- Migration separates Expand, protocol migration, semantic activation, and later Contract; this is current-course synthesis, not a universal mandate for all migrations.
- Frozen old artifact evidence is stronger than a new-code compatibility mode.
- Expand-only old-binary compatibility does not imply post-activation rollback safety.
- The post-v2 frozen-old-server unfenced-finish counterexample remains explicit.
- Recognition of a rollback boundary is not itself a failure.
- Large infrastructure is not a default answer; broker/transaction changes do not automatically solve external exactly-once.
- Permanently disabling retry would also fail the post-decision product requirement.
- Staged change topology is recommended for bounded claims/evidence/reversal, not for a fixed commit count.
- Agent implementation authority does not include product guarantee, architecture expansion, merge, activation, or residual-risk authority.
- Independent verification and independent review remain distinct after the M12 rewrite; M13 combines both and requires human/policy adjudication.
- Production evidence is contract-oriented; diagnostic identity and aggregate metric labels remain distinct.
- Instructor reference is not a canonical implementation and does not solve the listed production-grade residual risks.
- M13 remains 30% of the course grade; the internal 100-point rubric keeps the merge-base `20/15/15/15/15/10/10` distribution and the original `-20/-20/-15/-15/-10/-10` automatic-deduction weights.
- The course-closing working definition of Software Engineering is preserved verbatim in substance: maintaining boundaries, contracts, invariants, and mental models so humans or Agents can safely continue changing complex software.

## 6. Temporal/state-model review

The rewrite preserves the relevant temporal distinctions:

```text
logical job
  != execution attempt

current attempt authority
  != old process definitely stopped

state-fencing success
  != external-effect exactly-once

schema expanded
  != new semantics activated

old binary can read expanded rows
  != old binary can safely interpret post-v2 semantic state

protocol supported
  != recovery activation authorized
```

Lab evidence and case analysis use the same phases. Stale finish/heartbeat are judged against the current attempt at message arrival; a stale transition being rejected does not retroactively assert that the external effect never happened.

## 7. Lab executability and proof obligations

The Lab was rewritten as an execution document rather than prose chapter. The required path now has explicit closure:

1. baseline commands and raw output;
2. first-pass issue review before decision pack;
3. frozen issue-review checkpoint;
4. human-decision delta;
5. system model / contract / design memo / compatibility matrix;
6. staged plan and bounded Agent delegation;
7. one-stage-at-a-time implementation;
8. eight mandatory evidence clusters;
9. production evidence + rollout/rollback plan;
10. separate Review Agent context/session;
11. human adjudication / merge-rollout closure;
12. retrospective.

The eight mandatory evidence clusters preserve the old Lab's A–H obligations: claim race, schema Expand/frozen v1, attempt fencing, legacy finish boundary, recovery policy, external duplicate negative control, activation gate, rollback boundary.

The final submission layout remains twelve numbered artifacts plus `EVIDENCE.md`. M13 remains 30% of the course grade; its internal rubric remains 100 points with the original 20/15/15/15/15/10/10 distribution, and the merge-base automatic deductions keep their original -20/-20/-15/-15/-10/-10 weights.

## 8. Instructor-reference provenance clarification

The old source audit and instructor case already said the reference implementation was run in a **temporary solution copy** and recorded `14 passed`, frozen-v1 Expand compatibility, duplicate external effects despite state fencing, and an unsafe old-server rollback counterexample after v2 activation.

A provenance clarification was added: that temporary reference solution is not shipped as the canonical starter/student oracle. Therefore its recorded `14 passed` is instructor reference evidence, not evidence a student can cite for their own candidate. Student acceptance still requires independently generated runtime evidence in their working copy.

This does not change the historical reference claim; it narrows how that claim may be used.

## 9. Abstraction dependency sweep

The key dependency boundary is the human decision reveal.

Before that boundary, the rewritten module may use words already present in the issue/starter such as `lease`, `requeue`, old `finish`, worker identity absence, exactly-once request, and rollback request. It does **not** present `attempt` as the selected state model, `manual`/`automatic_at_least_once` as the selected product contract, or the activation gate as the selected rollout policy.

After the decision reveal, those terms are introduced as consequences of D1–D7 and can be reused throughout migration, evidence, review, and rollout reasoning.

The Lab necessarily names those concepts after Phase 2 because the decision pack has then been read; its Phase 1 issue-review instructions do not disclose the solution contract. A second synonym-level sweep caught one pre-decision use of `state fencing` in the Lab's boundary list; it was replaced with the observable `TaskForge local lifecycle state` framing so the D1 fencing vocabulary is not hinted before the reveal.

## 10. Design-decision dependency sweep

Specific reference choices remain conditional:

- jobs-table attempt columns vs separate attempts table;
- conditional update/CAS vs explicit transaction;
- exact stage/commit decomposition;
- exact production signal naming;
- stronger workload-specific external-effect guarantees if an effect owner supplies idempotency/fencing.

The human decision establishes required semantics, not these implementation details. Reviewer preference cannot silently become specification.

## 11. Compression / rhythm review

The module was reduced from a long heading/checklist index into a smaller number of episodes with prose as the default reasoning unit. The Lab intentionally remains structured because it is an execution contract. The instructor case remains evidence-first and reference-oriented.

Compression is not itself acceptance evidence. The relevant check is whether every preserved qualifier/non-goal above remains findable and whether a cold reader encounters the need for each abstraction before its first normative use.

## 12. Reviewer focus

Independent review of this PR should particularly check:

- whether the pre-decision module truly avoids leaking D1–D7 design conclusions while still explaining why the original issue is blocked;
- whether the post-decision attempt/lease/fencing narrative distinguishes state authority from external-effect authority;
- whether legacy `manual` recovery and v1 completion compatibility remain scoped precisely;
- whether claim-race safety is expressed as a history property, not a final-row property;
- whether migration distinguishes representation expand, protocol coexistence, semantic activation, and later contract removal;
- whether frozen-old evidence and rollback boundary keep their phase qualifiers;
- whether the Lab still contains all eight required evidence obligations and remains directly executable by a student;
- whether independent verification / Review Agent / human adjudication preserve the M12 authority model;
- whether the instructor reference is clearly non-canonical and its historical `14 passed` record is not offered as student acceptance evidence;
- whether no new external normative claim was introduced beyond the existing M13 source audit.
