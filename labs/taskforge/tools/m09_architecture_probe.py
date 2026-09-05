from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModuleFacts:
    name: str
    imports_state: bool
    reads_state: bool
    mutates_state: bool
    mutates_job_status: bool


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "taskforge"


def _module_name(path: Path) -> str:
    return path.stem


def _attribute_chain(node: ast.AST) -> tuple[str, ...] | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return None


def analyze_module(path: Path) -> ModuleFacts:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports_state = False
    reads_state = False
    mutates_state = False
    mutates_job_status = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "taskforge":
            if any(alias.name == "state" for alias in node.names):
                imports_state = True

        if isinstance(node, ast.Attribute):
            chain = _attribute_chain(node)
            if chain and len(chain) >= 2 and chain[0] == "state":
                reads_state = True

        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets: list[ast.AST]
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            else:
                targets = [node.target]
            for target in targets:
                chain = _attribute_chain(target)
                if chain and len(chain) >= 2 and chain[0] == "state":
                    mutates_state = True
                if isinstance(target, ast.Attribute) and chain and chain[-1] == "status":
                    mutates_job_status = True
                if isinstance(target, ast.Subscript):
                    value_chain = _attribute_chain(target.value)
                    if value_chain and value_chain[:2] == ("state", "jobs"):
                        mutates_state = True

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            chain = _attribute_chain(node.func)
            if chain and chain[:2] == ("state", "jobs") and chain[-1] in {
                "clear",
                "pop",
                "popitem",
                "setdefault",
                "update",
            }:
                mutates_state = True

    return ModuleFacts(
        name=_module_name(path),
        imports_state=imports_state,
        reads_state=reads_state,
        mutates_state=mutates_state,
        mutates_job_status=mutates_job_status,
    )


def main() -> int:
    facts = [
        analyze_module(path)
        for path in sorted(PACKAGE.glob("*.py"))
        if path.name != "__init__.py"
    ]

    direct_state = sorted(f.name for f in facts if f.imports_state or f.reads_state)
    lifecycle_mutators = sorted(f.name for f in facts if f.mutates_job_status)

    expected_direct_state = [
        "concurrent_claim",
        "legacy_audit",
        "metrics",
        "service",
        "worker",
    ]
    expected_lifecycle_mutators = ["concurrent_claim", "service", "worker"]

    if direct_state != expected_direct_state:
        raise AssertionError(
            "M09 baseline direct-state topology changed; expected "
            f"{expected_direct_state!r}, got {direct_state!r}"
        )
    if lifecycle_mutators != expected_lifecycle_mutators:
        raise AssertionError(
            "M09 baseline lifecycle-writer topology changed; expected "
            f"{expected_lifecycle_mutators!r}, got {lifecycle_mutators!r}"
        )

    print("[DIRECT STATE DEPENDENCIES] " + ", ".join(direct_state))
    print("[LIFECYCLE MUTATORS] " + ", ".join(lifecycle_mutators))
    print(
        "[LONG-LIVED SURFACES] public_api, snapshot schema, audit output, external effect protocol"
    )
    print(
        "[ARCHITECTURE PRESSURE] semantic authority is not aligned with module/process boundaries"
    )
    print(
        "M09 baseline inventory complete: model consequences before choosing deployment topology"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
