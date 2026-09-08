#!/usr/bin/env python3
"""Probe a built course site through Python's ordinary static HTTP server."""

from __future__ import annotations

import argparse
import json
import threading
from contextlib import ExitStack
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from html.parser import HTMLParser
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import urlopen

import site_model


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        pass


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for key, value in attrs:
            if key == "href" and value:
                self.hrefs.append(value)
                return


def status(url: str) -> int:
    try:
        with urlopen(url, timeout=5) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


def verify(dist: Path, model_path: Path = site_model.GENERATED_MODEL) -> None:
    model = json.loads(model_path.read_text(encoding="utf-8"))
    base = site_model.site_base()

    with ExitStack() as stack:
        if base == "/":
            serve_root = dist.resolve()
        else:
            # Model how a generic host mounts the same artifact below a base
            # path without teaching the HTTP server any rewrite behavior.
            serve_root = Path(stack.enter_context(TemporaryDirectory()))
            mount = serve_root.joinpath(*base.strip("/").split("/"))
            mount.parent.mkdir(parents=True, exist_ok=True)
            copytree(dist.resolve(), mount)

        handler = partial(QuietHandler, directory=str(serve_root))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"

        try:
            failures: list[str] = []
            internal_urls: set[str] = set()
            for page in model["pages"]:
                route = site_model.route_with_base(page["route"])
                code = status(origin + route)
                if code != 200:
                    failures.append(f"visible route {route!r} returned HTTP {code}")

                output = dist / site_model.route_to_output(page["route"])
                parser = LinkParser()
                parser.feed(output.read_text(encoding="utf-8"))
                for href in parser.hrefs:
                    absolute = urlsplit(urljoin(origin + route, href))
                    if absolute.scheme not in {"http", "https"}:
                        continue
                    if absolute.netloc != urlsplit(origin).netloc:
                        continue
                    internal_urls.add(
                        urlunsplit((absolute.scheme, absolute.netloc, absolute.path, absolute.query, ""))
                    )

            for url in sorted(internal_urls):
                code = status(url)
                if code != 200:
                    failures.append(f"rendered internal link {url!r} returned HTTP {code}")

            for page in model["excluded_canonical"]:
                route = site_model.route_with_base(page["route"])
                code = status(origin + route)
                if code != 404:
                    failures.append(f"excluded route {route!r} returned HTTP {code}, expected 404")

            if failures:
                raise RuntimeError(
                    "portable static HTTP verification failed:\n" + "\n".join(failures)
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print(
        "static HTTP verification: PASS "
        f"({len(model['pages'])} visible routes; {len(internal_urls)} rendered internal links; "
        f"base={base}; generic stdlib static server)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=site_model.GENERATED_MODEL)
    args = parser.parse_args()
    verify(args.dist, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
