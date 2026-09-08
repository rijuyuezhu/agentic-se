#!/usr/bin/env python3
"""Verify the assembled GitHub Pages bundle through a generic static server."""

from __future__ import annotations

import argparse
import os
import threading
from contextlib import ExitStack
from functools import partial
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import urlopen


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        pass


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        wanted = {
            "a": "href",
            "link": "href",
            "script": "src",
            "img": "src",
        }.get(tag)
        if not wanted:
            return
        for key, value in attrs:
            if key == wanted and value:
                self.urls.append(value)
                return


def normalize_base(value: str | None) -> str:
    if not value or value == "/":
        return "/"
    return "/" + value.strip("/") + "/"


def status(url: str) -> int:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


def route_for_html(path: Path, dist: Path, base: str) -> str:
    rel = path.relative_to(dist).as_posix()
    if rel == "index.html":
        return base
    if rel.endswith("/index.html"):
        return base + rel[: -len("index.html")]
    return base + rel


def verify(dist: Path, base: str) -> None:
    dist = dist.resolve()
    required = ["index.html", "student/index.html", "teacher/index.html", "all/index.html"]
    missing = [item for item in required if not (dist / item).is_file()]
    if missing:
        raise RuntimeError(f"Pages bundle is missing required entries: {missing}")

    with ExitStack() as stack:
        if base == "/":
            serve_root = dist
        else:
            serve_root = Path(stack.enter_context(TemporaryDirectory()))
            mount = serve_root.joinpath(*base.strip("/").split("/"))
            mount.parent.mkdir(parents=True, exist_ok=True)
            copytree(dist, mount)

        handler = partial(QuietHandler, directory=str(serve_root))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"

        try:
            failures: list[str] = []
            internal_urls: set[str] = set()
            html_files = sorted(dist.rglob("*.html"))

            for route in (base, base + "student/", base + "teacher/", base + "all/"):
                code = status(origin + route)
                if code != 200:
                    failures.append(f"entry route {route!r} returned HTTP {code}")

            for html in html_files:
                route = route_for_html(html, dist, base)
                parser = ResourceParser()
                parser.feed(html.read_text(encoding="utf-8"))
                for raw in parser.urls:
                    absolute = urlsplit(urljoin(origin + route, raw))
                    if absolute.scheme not in {"http", "https"}:
                        continue
                    if absolute.netloc != urlsplit(origin).netloc:
                        continue
                    if not absolute.path.startswith(base):
                        failures.append(
                            f"internal URL escaped Pages base {base!r}: {absolute.path!r} from {route!r}"
                        )
                        continue
                    internal_urls.add(
                        urlunsplit((absolute.scheme, absolute.netloc, absolute.path, absolute.query, ""))
                    )

            for url in sorted(internal_urls):
                code = status(url)
                if code != 200:
                    failures.append(f"internal resource {url!r} returned HTTP {code}")

            if failures:
                raise RuntimeError("Pages bundle verification failed:\n" + "\n".join(failures))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print(
        "Pages bundle verification: PASS "
        f"({len(html_files)} HTML files; {len(internal_urls)} internal resources; base={base})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--base", default=os.environ.get("COURSE_PAGES_BASE", "/agentic-se/"))
    args = parser.parse_args()
    verify(args.dist, normalize_base(args.base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
