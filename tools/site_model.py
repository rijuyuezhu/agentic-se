#!/usr/bin/env python3
"""Derive and verify the VitePress site model from canonical course content."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import content_model

ROOT = content_model.ROOT
SITE_DIR = ROOT / "site"
GENERATED_MODEL = SITE_DIR / ".generated" / "site-model.json"
VISIBILITY_CHOICES = ("student", "instructor", "all")


def site_base() -> str:
    raw = os.environ.get("COURSE_SITE_BASE", "/")
    if not raw or raw == "/":
        return "/"
    return "/" + raw.strip("/") + "/"


def route_with_base(route: str) -> str:
    return site_base() + route.lstrip("/")


def path_to_route(relpath: str) -> str:
    path = Path(relpath)
    if path.name.lower() == "readme.md":
        parent = path.parent.as_posix()
        return "/" if parent == "." else f"/{parent}/"
    if path.name.lower() == "index.md":
        parent = path.parent.as_posix()
        return "/" if parent == "." else f"/{parent}/"
    # Keep ordinary page URLs identical to the portable static artifact name.
    # VitePress clean URLs require host-side rewrites from /foo -> /foo.html;
    # #5 requires the artifact to work on generic static hosting without that
    # undeclared server capability.
    return "/" + path.with_suffix(".html").as_posix()


def path_to_rewrite(relpath: str) -> str | None:
    path = Path(relpath)
    if path.name.lower() != "readme.md":
        return None
    return "index.md" if path.parent == Path(".") else (path.parent / "index.md").as_posix()


def route_to_output(route: str) -> str:
    if route == "/":
        return "index.html"
    cleaned = route.strip("/")
    if route.endswith("/"):
        return f"{cleaned}/index.html"
    if cleaned.endswith(".html"):
        return cleaned
    raise RuntimeError(f"non-directory site route must end in .html: {route!r}")


def _markdown_paths() -> set[str]:
    paths: set[str] = set()
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in {".git", "site"}:
            continue
        paths.add(rel.as_posix())
    return paths


def build_site_model(mode: str) -> dict[str, object]:
    pages, errors = content_model.validate()
    if errors:
        raise RuntimeError("content validation failed:\n" + "\n".join(errors))

    visible_manifest = content_model.manifest(pages, mode)
    all_manifest = content_model.manifest(pages, "all")
    visible_entries = visible_manifest["pages"]
    assert isinstance(visible_entries, list)
    all_entries = all_manifest["pages"]
    assert isinstance(all_entries, list)

    visible_paths = {entry["path"] for entry in visible_entries}
    all_by_path = {entry["path"]: entry for entry in all_entries}

    enriched_pages: list[dict[str, object]] = []
    rewrites: dict[str, str] = {}
    for raw_entry in visible_entries:
        entry = dict(raw_entry)
        path = str(entry["path"])
        entry["route"] = path_to_route(path)
        rewrite = path_to_rewrite(path)
        if rewrite is not None:
            rewrites[path] = rewrite
        enriched_pages.append(entry)

    excluded_canonical = []
    for path, raw_entry in sorted(all_by_path.items()):
        if path in visible_paths:
            continue
        entry = dict(raw_entry)
        entry["route"] = path_to_route(path)
        excluded_canonical.append(entry)

    src_exclude = sorted(_markdown_paths() - visible_paths)
    # VitePress has srcDir="..". Never discover renderer implementation files as pages.
    src_exclude.append("site/**")

    main_path = sorted(
        (entry for entry in enriched_pages if entry["order"] is not None),
        key=lambda entry: int(entry["order"]),
    )
    if [entry["order"] for entry in main_path] != list(range(15)):
        raise RuntimeError("derived site Main Path must be exactly order 0..14")

    return {
        "visibility": mode,
        "pages": enriched_pages,
        "excluded_canonical": excluded_canonical,
        "main_path": main_path,
        "src_exclude": src_exclude,
        "rewrites": rewrites,
    }


def write_site_model(mode: str, output: Path = GENERATED_MODEL) -> dict[str, object]:
    model = build_site_model(mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return model


def _search_index_text(dist: Path) -> str:
    chunks = sorted((dist / "assets" / "chunks").glob("@localSearchIndex*.js"))
    if not chunks:
        raise RuntimeError("VitePress local-search index chunk not found")
    return "\n".join(path.read_text(encoding="utf-8") for path in chunks)


def verify_output(mode: str, dist: Path, model_path: Path = GENERATED_MODEL) -> None:
    if not model_path.exists():
        raise RuntimeError(f"generated site model does not exist: {model_path}")
    model = json.loads(model_path.read_text(encoding="utf-8"))
    if model.get("visibility") != mode:
        raise RuntimeError(
            f"site model visibility mismatch: expected {mode!r}, got {model.get('visibility')!r}"
        )
    if not dist.is_dir():
        raise RuntimeError(f"site build directory does not exist: {dist}")

    pages = model["pages"]
    excluded = model["excluded_canonical"]
    expected_html = {route_to_output(page["route"]) for page in pages}
    actual_html = {
        path.relative_to(dist).as_posix() for path in dist.rglob("*.html")
    }

    missing = sorted(expected_html - actual_html)
    if missing:
        raise RuntimeError(f"site build is missing canonical routes: {missing}")

    allowed_extra = {"404.html"}
    unexpected = sorted(actual_html - expected_html - allowed_extra)
    if unexpected:
        raise RuntimeError(
            "site build generated non-canonical Markdown routes: " + repr(unexpected)
        )

    leaked_routes = []
    for page in excluded:
        output = route_to_output(page["route"])
        if output in actual_html:
            leaked_routes.append(output)
    if leaked_routes:
        raise RuntimeError(
            "site build generated excluded canonical routes: " + repr(sorted(leaked_routes))
        )

    search_text = _search_index_text(dist)
    search_leaks = [
        page["route"]
        for page in excluded
        if page["route"] in search_text or route_with_base(page["route"]) in search_text
    ]
    if search_leaks:
        raise RuntimeError(
            "search index contains excluded canonical routes: " + repr(sorted(search_leaks))
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="write a derived site model")
    prepare.add_argument("--visibility", choices=VISIBILITY_CHOICES, default="student")
    prepare.add_argument("--output", type=Path, default=GENERATED_MODEL)

    verify = sub.add_parser("verify", help="verify a static site build")
    verify.add_argument("--visibility", choices=VISIBILITY_CHOICES, default="student")
    verify.add_argument("--dist", type=Path, default=SITE_DIR / ".vitepress" / "dist")
    verify.add_argument("--model", type=Path, default=GENERATED_MODEL)

    args = parser.parse_args()
    if args.command == "prepare":
        model = write_site_model(args.visibility, args.output)
        print(
            f"site model: {args.visibility} ({len(model['pages'])} pages, "
            f"{len(model['excluded_canonical'])} canonical pages excluded)"
        )
        return 0

    verify_output(args.visibility, args.dist, args.model)
    print(f"site verification: PASS ({args.visibility})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
