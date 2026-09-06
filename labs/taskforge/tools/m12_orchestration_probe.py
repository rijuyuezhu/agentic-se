from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKETS = ROOT / "agent-contracts" / "m12"

REQUIRED_TASK_FIELDS = {
    "goal",
    "context",
    "non_goals",
    "contracts_and_invariants",
    "allowed_write_paths",
    "forbidden_actions",
    "evidence_contract",
    "stages",
    "stop_conditions",
    "escalate_when",
    "authority_matrix",
    "done_when",
}

REQUIRED_AUTHORITY_ROLES = {
    "exploration_agent",
    "implementation_agent",
    "review_agent",
    "human_only",
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((PACKETS / name).read_text(encoding="utf-8"))


def audit_task_contract(task: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    missing = sorted(REQUIRED_TASK_FIELDS - task.keys())
    if missing:
        findings.append("missing task fields: " + ", ".join(missing))
        return findings

    empty = [field for field in REQUIRED_TASK_FIELDS if not task[field]]
    if empty:
        findings.append("empty task fields: " + ", ".join(sorted(empty)))

    matrix = task.get("authority_matrix", {})
    missing_roles = sorted(REQUIRED_AUTHORITY_ROLES - matrix.keys())
    if missing_roles:
        findings.append("missing authority roles: " + ", ".join(missing_roles))

    if not any("SLO" in item or "denominator" in item for item in task["forbidden_actions"]):
        findings.append("task does not protect M11 acceptance measurement from being rewritten")

    if not any("side effect" in item.lower() or "no Job" in item for item in task["contracts_and_invariants"]):
        findings.append("task does not state a no-side-effect rejection invariant")

    return findings


def _path_allowed(path: str, prefixes: list[str]) -> bool:
    return any(path == prefix or path.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def audit_agent_plan(
    task: dict[str, Any], plan: dict[str, Any], *, authorized_decision: dict[str, Any] | None = None
) -> tuple[list[str], list[str]]:
    violations: list[str] = []
    escalations: list[str] = []

    allowed = task["allowed_write_paths"]
    for path in plan.get("planned_writes", []):
        if not _path_allowed(path, allowed):
            violations.append(f"write outside authorized scope: {path}")

    actions = "\n".join(plan.get("planned_actions", [])).lower()
    forbidden_patterns = {
        "change SLO / acceptance target": ["change m11", "slo target", "target from", "lower"],
        "change SLI denominator without authority": ["exclude rejected", "denominator"],
        "weaken/delete existing evidence": ["delete the old", "delete", "weaken"],
        "merge without human authority": ["merge to main", "merge"],
        "deploy without human authority": ["deploy"],
    }
    for label, patterns in forbidden_patterns.items():
        if any(pattern in actions for pattern in patterns):
            violations.append(label)

    open_questions = plan.get("open_questions", [])
    if open_questions:
        escalations.extend(open_questions)

    authorization = plan.get("authorization")
    if authorization:
        if authorized_decision is None:
            violations.append("plan cites authorization but no human decision record was supplied")
        elif authorization != authorized_decision.get("decision_id"):
            violations.append("plan authorization id does not match human decision record")
    elif not open_questions:
        # A no-question implementation plan for this task should cite the human decision
        # because the task deliberately leaves public result shape and policy threshold open.
        violations.append("implementation plan has no unresolved questions but cites no human authorization")

    return sorted(set(violations)), escalations


def decision(violations: list[str], escalations: list[str]) -> str:
    if violations:
        return "REJECT_PLAN"
    if escalations:
        return "STOP_AND_ESCALATE"
    return "AUTHORIZED_TO_IMPLEMENT"


def main() -> int:
    vague = _load("vague-task.json")
    engineered = _load("engineered-task.json")
    unsafe = _load("unsafe-agent-plan.json")
    bounded = _load("bounded-agent-plan.json")
    human = _load("human-decision.json")
    authorized = _load("authorized-agent-plan.json")

    vague_findings = audit_task_contract(vague)
    engineered_findings = audit_task_contract(engineered)
    unsafe_violations, unsafe_escalations = audit_agent_plan(engineered, unsafe)
    bounded_violations, bounded_escalations = audit_agent_plan(engineered, bounded)
    authorized_violations, authorized_escalations = audit_agent_plan(
        engineered, authorized, authorized_decision=human
    )

    print("[VAGUE TASK]")
    print(f"decision=INSUFFICIENT_CONTRACT findings={len(vague_findings)}")
    for finding in vague_findings:
        print(f"- {finding}")

    print("\n[ENGINEERED TASK]")
    print(
        "decision=STRUCTURALLY_COMPLETE"
        if not engineered_findings
        else "decision=CONTRACT_DEFECT"
    )
    for finding in engineered_findings:
        print(f"- {finding}")

    print("\n[UNSAFE IMPLEMENTATION PLAN]")
    print(f"decision={decision(unsafe_violations, unsafe_escalations)}")
    for finding in unsafe_violations:
        print(f"- authority violation: {finding}")

    print("\n[BOUNDED PLAN BEFORE HUMAN DECISION]")
    print(f"decision={decision(bounded_violations, bounded_escalations)}")
    for question in bounded_escalations:
        print(f"- escalation: {question}")

    print("\n[AUTHORIZED PLAN AFTER HUMAN DECISION]")
    print(f"decision={decision(authorized_violations, authorized_escalations)}")
    print(f"authorization={authorized.get('authorization')}")
    for finding in authorized_violations:
        print(f"- authority violation: {finding}")

    expected = {
        "vague": bool(vague_findings),
        "engineered": not engineered_findings,
        "unsafe": decision(unsafe_violations, unsafe_escalations) == "REJECT_PLAN",
        "bounded": decision(bounded_violations, bounded_escalations) == "STOP_AND_ESCALATE",
        "authorized": decision(authorized_violations, authorized_escalations)
        == "AUTHORIZED_TO_IMPLEMENT",
    }
    if not all(expected.values()):
        raise AssertionError(f"unexpected M12 orchestration baseline: {expected}")

    print("\nM12 authority/orchestration baseline reproduced deterministically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
