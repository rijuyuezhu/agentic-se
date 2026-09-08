#!/usr/bin/env python3
"""Validate and expose the front-end-independent course content graph."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_FIELDS = {"id", "type", "visibility", "order", "related"}
CONTENT_TYPES = {
    "reference",
    "module",
    "lab",
    "case_study",
    "source_audit",
    "extension",
    "practicum",
}
VISIBILITIES = {"student", "instructor", "internal"}
VISIBILITY_TARGETS = {
    "student": {"student"},
    "instructor": {"student", "instructor"},
    "internal": {"student", "instructor", "internal"},
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
INDENTED_HEADING_RE = re.compile(r"^[ \t]+#{1,6}[ \t]+")
CONTAINER_HEADING_RE = re.compile(
    r"^\s*(?:(?:>\s*)|(?:(?:[-+*]|\d+[.)])\s+))+#{1,6}[ \t]+"
)
CLOSING_ATX_HASH_RE = re.compile(r"[ \t]+#+[ \t]*$")
FENCE_CANDIDATE_RE = re.compile(r"^( *)(`+|~+)(.*)$")
LINK_RE = re.compile(r"(?<!!)\[[^\[\]\n]+\]\(([^()\n]+)\)")
IMAGE_RE = re.compile(r"!\[[^\[\]\n]*\]\(([^()\n]+)\)")
EXTERNAL_URL_RE = re.compile(r"https?://[^\s)>]+")
CHARACTER_REFERENCE_RE = re.compile(
    r"&(?:#[0-9]+|#[xX][0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);"
)
TASK_LIST_RE = re.compile(
    r"^[ \t]*(?:(?:[-+*])|(?:\d+[.)]))[ \t]+\[[ xX]\](?=[ \t]+|$)"
)
SETEXT_UNDERLINE_RE = re.compile(r"^\s*(?:>\s*)*(?:=+|-+)\s*$")
AUTOLINK_RE = re.compile(
    r"<(?:(?:https?://|mailto:)[^>]+|[^<>\s@]+@[^<>\s@]+\.[^<>\s@]+)>",
    re.IGNORECASE,
)
RAW_HTML_RE = re.compile(r"<(?:!--|\?|!\[CDATA\[|![A-Za-z]|/?[A-Za-z])")
SOURCE_AUDIT_DATE_RE = re.compile(
    r"(?:审计日期|审计/复核日期|Freshness note)[^\n]*20\d{2}-\d{2}-\d{2}",
    re.IGNORECASE,
)


class ContentError(ValueError):
    pass


@dataclass(frozen=True)
class Page:
    path: Path
    id: str
    type: str
    visibility: str
    title: str
    order: int | None
    related: tuple[str, ...]

    @property
    def relpath(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def _parse_scalar(value: str, *, path: Path, key: str) -> object:
    value = value.strip()
    if not value:
        raise ContentError(f"{path}: frontmatter field {key!r} has an empty value")

    if value.startswith("["):
        if not value.endswith("]"):
            raise ContentError(f"{path}: malformed inline list for {key!r}")
        body = value[1:-1].strip()
        if not body:
            return []
        items: list[str] = []
        for raw in body.split(","):
            item = raw.strip()
            if len(item) >= 2 and item[0] == item[-1] and item[0] in {'"', "'"}:
                item = item[1:-1]
            if not item:
                raise ContentError(f"{path}: empty item in frontmatter list {key!r}")
            items.append(item)
        return items

    if re.fullmatch(r"-?\d+", value):
        return int(value)

    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> tuple[dict[str, object] | None, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None, lines

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ContentError(f"{path}: opening frontmatter has no closing ---") from exc

    data: dict[str, object] = {}
    for lineno, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ContentError(
                f"{path}:{lineno}: frontmatter must use simple 'key: value' entries"
            )
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise ContentError(f"{path}:{lineno}: invalid frontmatter key {key!r}")
        if key in data:
            raise ContentError(f"{path}:{lineno}: duplicate frontmatter key {key!r}")
        data[key] = _parse_scalar(raw_value, path=path, key=key)

    return data, lines[end + 1 :]


def _mask_inline_code(line: str) -> tuple[str, str | None]:
    """Mask the canonical inline-code subset while preserving character offsets."""
    if r"\`" in line:
        return line, "backslash-escaped backticks are not allowed in canonical Markdown"
    runs = list(re.finditer(r"`+", line))
    if not runs:
        return line, None
    if any(len(match.group(0)) != 1 for match in runs):
        return line, "inline code supports only paired single backticks on one line"
    if len(runs) % 2:
        return line, "unmatched inline-code backtick; use paired single backticks on one line"

    masked = list(line)
    for opener, closer in zip(runs[0::2], runs[1::2], strict=True):
        masked[opener.start() : closer.end()] = " " * (closer.end() - opener.start())
    return "".join(masked), None


def markdown_structure(
    lines: list[str],
) -> tuple[
    list[tuple[int, int, str]],
    list[tuple[int, str]],
    list[tuple[int, str]],
    list[tuple[int, str]],
]:
    headings: list[tuple[int, int, str]] = []
    links: list[tuple[int, str]] = []
    bare_urls: list[tuple[int, str]] = []
    syntax_errors: list[tuple[int, str]] = []
    fence: str | None = None
    previous_line = ""

    for lineno, line in enumerate(lines, start=1):
        fence_candidate = FENCE_CANDIDATE_RE.match(line)
        if fence is not None:
            if fence_candidate is not None:
                indent, run, rest = fence_candidate.groups()
                if len(indent) <= 3 and run[0] == fence and len(run) >= 3 and not rest.strip():
                    if len(run) != 3:
                        syntax_errors.append(
                            (lineno, "fenced code blocks support exactly three matching backticks/tildes")
                        )
                    # A longer run closes the CommonMark fence. End our state too
                    # after reporting the unsupported syntax so following prose is
                    # never silently hidden from link/visibility validation.
                    fence = None
                    previous_line = ""
                    continue
            continue

        if fence_candidate is not None and len(fence_candidate.group(2)) >= 3:
            indent, run, info = fence_candidate.groups()
            if len(indent) > 3:
                syntax_errors.append(
                    (lineno, "fence-like syntax indented four or more spaces is not allowed")
                )
                previous_line = line
                continue
            if len(run) != 3:
                syntax_errors.append(
                    (lineno, "fenced code blocks support exactly three backticks or tildes")
                )
                previous_line = line
                continue
            if run[0] in info:
                syntax_errors.append(
                    (lineno, "fence info string may not contain the fence marker character")
                )
                previous_line = line
                continue
            fence = run[0]
            previous_line = ""
            continue

        # Canonical pages intentionally use a small, fail-closed Markdown
        # authoring subset. The validator is not a CommonMark parser, so
        # constructs that can change heading/link semantics without being
        # understood here are rejected rather than silently ignored.
        prose, inline_code_error = _mask_inline_code(line)
        if inline_code_error is not None:
            syntax_errors.append((lineno, inline_code_error))
            # Do not guess which bytes are code when delimiters are unsupported.
            # Scan the original line as prose as well; the syntax error already
            # makes the page fail closed.
            prose = line

        simple_destinations = list(LINK_RE.finditer(prose)) + list(IMAGE_RE.finditer(prose))
        bracket_scan = list(prose)
        for destination in simple_destinations:
            start, end = destination.span()
            bracket_scan[start:end] = " " * (end - start)
        task_marker = TASK_LIST_RE.match(prose)
        if task_marker is not None:
            start, end = task_marker.span()
            bracket_scan[start:end] = " " * (end - start)
        remaining_brackets = "".join(bracket_scan)
        if "[" in remaining_brackets or "]" in remaining_brackets:
            syntax_errors.append(
                (
                    lineno,
                    "unsupported square-bracket Markdown syntax; reference-style links are not allowed; "
                    "use simple inline links/images or task-list markers",
                )
            )
        if previous_line.strip() and SETEXT_UNDERLINE_RE.match(line):
            syntax_errors.append(
                (lineno, "Setext headings are not allowed; use ATX # headings")
            )
        if INDENTED_HEADING_RE.match(prose):
            syntax_errors.append(
                (lineno, "indented ATX headings are not allowed; headings must start at column 0")
            )
        if CONTAINER_HEADING_RE.match(prose):
            syntax_errors.append(
                (
                    lineno,
                    "headings inside blockquote/list containers are not allowed; use top-level ATX headings",
                )
            )
        if AUTOLINK_RE.search(prose):
            syntax_errors.append(
                (lineno, "angle-bracket autolinks are not allowed; use semantic inline links")
            )
        elif RAW_HTML_RE.search(prose):
            syntax_errors.append(
                (lineno, "raw HTML is not allowed in canonical Markdown")
            )

        match = HEADING_RE.match(line)
        if match:
            title = match.group(2)
            if CLOSING_ATX_HASH_RE.search(title):
                syntax_errors.append(
                    (lineno, "closing ATX heading hashes are not allowed in canonical Markdown")
                )
            headings.append((lineno, len(match.group(1)), title))

        if prose.count("](") != len(simple_destinations):
            syntax_errors.append(
                (
                    lineno,
                    "unsupported inline link/image syntax; use simple [text](target) or ![alt](target) "
                    "without nested brackets or raw parentheses in the destination",
                )
            )

        for link_match in simple_destinations:
            start, end = link_match.span(1)
            raw = line[start:end].strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1 : raw.index(">")]
            else:
                # Optional Markdown link titles are outside the target token.
                raw = raw.split(maxsplit=1)[0]
            if CHARACTER_REFERENCE_RE.search(raw):
                syntax_errors.append(
                    (
                        lineno,
                        "Markdown character references are not allowed in link/image destinations; "
                        "use raw or percent-encoded URL characters",
                    )
                )
            if "\\" in raw:
                syntax_errors.append(
                    (
                        lineno,
                        "backslash escapes are not allowed in link/image destinations; "
                        "use raw or percent-encoded URL characters",
                    )
                )
            links.append((lineno, raw))

        # Inline code may intentionally show a literal URL or command. The link
        # readability rule applies to prose, not code examples.
        for url_match in EXTERNAL_URL_RE.finditer(prose):
            before = prose[: url_match.start()]
            if before.endswith("](") or before.endswith("<"):
                continue
            bare_urls.append((lineno, url_match.group(0)))

        previous_line = line

    if fence is not None:
        syntax_errors.append(
            (len(lines) if lines else 1, "unclosed fenced code block in canonical Markdown")
        )

    return headings, links, bare_urls, syntax_errors


def _validate_metadata(path: Path, data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    unknown = set(data) - ALLOWED_FIELDS
    if unknown:
        errors.append(f"{path}: unknown frontmatter fields: {sorted(unknown)}")

    for key in ("id", "type", "visibility"):
        if key not in data:
            errors.append(f"{path}: missing required frontmatter field {key!r}")

    page_id = data.get("id")
    if not isinstance(page_id, str) or not ID_RE.fullmatch(page_id):
        errors.append(f"{path}: id must match {ID_RE.pattern}")

    page_type = data.get("type")
    if page_type not in CONTENT_TYPES:
        errors.append(f"{path}: type must be one of {sorted(CONTENT_TYPES)}")

    visibility = data.get("visibility")
    if visibility not in VISIBILITIES:
        errors.append(f"{path}: visibility must be one of {sorted(VISIBILITIES)}")

    order = data.get("order")
    if order is not None and not isinstance(order, int):
        errors.append(f"{path}: order must be an integer")

    related = data.get("related", [])
    if not isinstance(related, list) or not all(isinstance(x, str) for x in related):
        errors.append(f"{path}: related must be an inline list of content IDs")
    elif len(related) != len(set(related)):
        errors.append(f"{path}: related contains duplicate IDs")

    return errors


def required_content_paths() -> set[Path]:
    paths: set[Path] = {ROOT / "README.md", ROOT / "MATERIALS_REVIEW.md"}
    paths.update((ROOT / "modules").glob("*.md"))
    paths.update((ROOT / "labs").glob("*.md"))
    paths.update((ROOT / "case-studies").glob("*/*.md"))
    paths.update((ROOT / "extensions").glob("*.md"))
    # practicum/ is a mixed zone: the root course entry is mandatory, while
    # nested teaching pages opt into the graph by carrying frontmatter. This
    # lets repo-only harness notes/artifacts coexist without recursive
    # promotion into website content.
    paths.add(ROOT / "practicum" / "README.md")
    paths.update((ROOT / "reading-notes").glob("m[0-9][0-9]-source-audit.md"))
    for name in (
        "extensions-source-audit.md",
        "traditional-se-gap-map.md",
        "final-practicum-candidate-audit.md",
        "final-practicum-instructor-reference.md",
        "final-practicum-pilot.md",
    ):
        paths.add(ROOT / "reading-notes" / name)
    return {path.resolve() for path in paths if path.exists()}


def load_pages() -> tuple[list[Page], list[str], dict[Path, list[tuple[int, str]]]]:
    pages: list[Page] = []
    errors: list[str] = []
    page_links: dict[Path, list[tuple[int, str]]] = {}
    with_frontmatter: set[Path] = set()

    for path in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", ".venv", ".pytest_cache"} for part in path.parts):
            continue
        try:
            data, body = parse_frontmatter(path)
        except ContentError as exc:
            errors.append(str(exc))
            continue
        if data is None:
            continue

        resolved = path.resolve()
        with_frontmatter.add(resolved)
        metadata_errors = _validate_metadata(path.relative_to(ROOT), data)
        errors.extend(metadata_errors)
        if metadata_errors:
            continue

        headings, links, bare_urls, syntax_errors = markdown_structure(body)
        page_links[resolved] = links
        for lineno, reason in syntax_errors:
            errors.append(f"{path.relative_to(ROOT)}:{lineno}: {reason}")
        for lineno, url in bare_urls:
            errors.append(
                f"{path.relative_to(ROOT)}:{lineno}: bare external URL in prose; "
                f"use semantic Markdown link text: {url!r}"
            )

        if data["type"] == "source_audit" and not SOURCE_AUDIT_DATE_RE.search(
            "\n".join(body)
        ):
            errors.append(
                f"{path.relative_to(ROOT)}: source_audit must record an audit/review/freshness date"
            )
        h1s = [heading for heading in headings if heading[1] == 1]
        if len(h1s) != 1:
            errors.append(
                f"{path.relative_to(ROOT)}: canonical page must have exactly one semantic H1; found {len(h1s)}"
            )
            title = ""
        else:
            title = h1s[0][2]
            if not headings or headings[0][1] != 1:
                errors.append(
                    f"{path.relative_to(ROOT)}: the first semantic heading must be the page H1"
                )

        previous_level: int | None = None
        for lineno, level, _ in headings:
            if previous_level is not None and level > previous_level + 1:
                errors.append(
                    f"{path.relative_to(ROOT)}:{lineno}: heading level jumps from H{previous_level} to H{level}"
                )
            previous_level = level

        related = tuple(data.get("related", []))
        pages.append(
            Page(
                path=resolved,
                id=data["id"],  # type: ignore[arg-type]
                type=data["type"],  # type: ignore[arg-type]
                visibility=data["visibility"],  # type: ignore[arg-type]
                title=title,
                order=data.get("order") if isinstance(data.get("order"), int) else None,
                related=related,
            )
        )

    missing_frontmatter = required_content_paths() - with_frontmatter
    for path in sorted(missing_frontmatter):
        errors.append(
            f"{path.relative_to(ROOT)}: required canonical content page has no frontmatter"
        )

    return pages, errors, page_links


def _local_target(source: Path, raw_target: str) -> Path | None:
    if not raw_target or raw_target.startswith("#"):
        return None
    parsed = urlsplit(raw_target)
    if parsed.scheme or raw_target.startswith("//"):
        return None
    target_path = unquote(parsed.path)
    if not target_path:
        return None
    return (source.parent / target_path).resolve()


def validate() -> tuple[list[Page], list[str]]:
    pages, errors, page_links = load_pages()

    by_id: dict[str, Page] = {}
    by_path: dict[Path, Page] = {}
    for page in pages:
        if page.id in by_id:
            errors.append(
                f"duplicate content id {page.id!r}: {by_id[page.id].relpath} and {page.relpath}"
            )
        else:
            by_id[page.id] = page
        by_path[page.path] = page

    for page in pages:
        if page.id in page.related:
            errors.append(f"{page.relpath}: related may not contain its own id {page.id!r}")
        for target_id in page.related:
            target = by_id.get(target_id)
            if target is None:
                errors.append(f"{page.relpath}: related references unknown id {target_id!r}")
                continue
            if target.visibility not in VISIBILITY_TARGETS[page.visibility]:
                errors.append(
                    f"{page.relpath}: {page.visibility} page relates to page {target_id!r} "
                    f"outside its build visibility ({target.visibility})"
                )

    expected_modules = {f"M{i:02d}": i for i in range(14)}
    actual_modules = {page.id: page for page in pages if page.type == "module"}
    if set(actual_modules) != set(expected_modules):
        errors.append(
            "module IDs must be exactly M00..M13; "
            f"missing={sorted(set(expected_modules) - set(actual_modules))}, "
            f"extra={sorted(set(actual_modules) - set(expected_modules))}"
        )
    for module_id, expected_order in expected_modules.items():
        page = actual_modules.get(module_id)
        if page is not None and page.order != expected_order:
            errors.append(
                f"{page.relpath}: {module_id} must have order {expected_order}, got {page.order!r}"
            )

    final_practicum = by_id.get("final-practicum")
    if final_practicum is None:
        errors.append("missing required Final Practicum content id 'final-practicum'")
    elif final_practicum.type != "practicum" or final_practicum.order != 14:
        errors.append(
            f"{final_practicum.relpath}: final-practicum must be type practicum with order 14"
        )

    ordered = [page for page in pages if page.order is not None]
    seen_orders: dict[int, Page] = {}
    for page in ordered:
        if page.type not in {"module", "practicum"}:
            errors.append(f"{page.relpath}: only module/practicum Main Path pages may define order")
        assert page.order is not None
        if page.order in seen_orders:
            errors.append(
                f"duplicate Main Path order {page.order}: {seen_orders[page.order].relpath} and {page.relpath}"
            )
        else:
            seen_orders[page.order] = page
    if set(seen_orders) != set(range(15)):
        errors.append(
            f"Main Path orders must be exactly 0..14; got {sorted(seen_orders)}"
        )

    for source_path, links in page_links.items():
        source_page = by_path[source_path]
        for lineno, raw_target in links:
            target = _local_target(source_path, raw_target)
            if target is None:
                continue
            try:
                target.relative_to(ROOT.resolve())
            except ValueError:
                errors.append(
                    f"{source_page.relpath}:{lineno}: local Markdown link escapes repository root: "
                    f"{raw_target!r}"
                )
                continue
            if not target.exists():
                errors.append(
                    f"{source_page.relpath}:{lineno}: broken local Markdown link {raw_target!r}"
                )
                continue
            target_page = by_path.get(target)
            if (
                target_page is not None
                and target_page.visibility
                not in VISIBILITY_TARGETS[source_page.visibility]
            ):
                errors.append(
                    f"{source_page.relpath}:{lineno}: {source_page.visibility} page links to "
                    f"canonical page {target_page.id!r} outside its build visibility "
                    f"({target_page.visibility})"
                )

    for source_page in pages:
        hidden_pages = [
            page
            for page in pages
            if page.visibility not in VISIBILITY_TARGETS[source_page.visibility]
        ]
        if not hidden_pages:
            continue
        text = source_page.path.read_text(encoding="utf-8")
        for target_page in hidden_pages:
            relative_target = Path(
                os.path.relpath(target_page.path, source_page.path.parent)
            ).as_posix()
            if relative_target in text or target_page.relpath in text:
                errors.append(
                    f"{source_page.relpath}: {source_page.visibility} page exposes canonical path "
                    f"outside its build visibility: {target_page.relpath!r}"
                )

    return pages, errors


def visible_set(mode: str) -> set[str]:
    if mode == "student":
        return {"student"}
    if mode == "instructor":
        return {"student", "instructor"}
    if mode == "all":
        return VISIBILITIES
    raise AssertionError(mode)


def manifest(pages: list[Page], mode: str) -> dict[str, object]:
    allowed = visible_set(mode)
    visible_pages = [page for page in pages if page.visibility in allowed]
    visible_ids = {page.id for page in visible_pages}
    inverse: dict[str, list[str]] = {page.id: [] for page in visible_pages}
    for page in visible_pages:
        for target in page.related:
            if target in visible_ids:
                inverse[target].append(page.id)

    def sort_key(page: Page) -> tuple[int, int, str]:
        return (0 if page.order is not None else 1, page.order or 0, page.relpath)

    entries = []
    for page in sorted(visible_pages, key=sort_key):
        entries.append(
            {
                "id": page.id,
                "type": page.type,
                "visibility": page.visibility,
                "title": page.title,
                "path": page.relpath,
                "order": page.order,
                "related": [item for item in page.related if item in visible_ids],
                "related_by": sorted(inverse[page.id]),
            }
        )
    return {"visibility": mode, "pages": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="validate the canonical Markdown content graph")
    manifest_parser = sub.add_parser("manifest", help="emit a derived JSON content manifest")
    manifest_parser.add_argument(
        "--visibility",
        choices=("student", "instructor", "all"),
        default="student",
    )
    args = parser.parse_args()

    pages, errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"content validation failed: {len(errors)} error(s)", file=sys.stderr)
        return 1

    if args.command == "validate":
        counts: dict[str, int] = {}
        for page in pages:
            counts[page.type] = counts.get(page.type, 0) + 1
        print(f"content validation: PASS ({len(pages)} canonical pages)")
        print("types: " + ", ".join(f"{key}={counts[key]}" for key in sorted(counts)))
        return 0

    print(json.dumps(manifest(pages, args.visibility), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
