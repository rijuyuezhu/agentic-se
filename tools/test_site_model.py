#!/usr/bin/env python3
"""Regression tests for the derived course-site model."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import site_model


class SiteModelTests(unittest.TestCase):
    def test_route_mapping(self) -> None:
        self.assertEqual(site_model.path_to_route("README.md"), "/")
        self.assertEqual(site_model.path_to_route("practicum/README.md"), "/practicum/")
        self.assertEqual(site_model.path_to_route("extensions/index.md"), "/extensions/")
        self.assertEqual(
            site_model.path_to_route("modules/07-concurrency-lifecycle-failure.md"),
            "/modules/07-concurrency-lifecycle-failure.html",
        )
        self.assertEqual(
            site_model.route_to_output("/modules/07-concurrency-lifecycle-failure.html"),
            "modules/07-concurrency-lifecycle-failure.html",
        )
        with self.assertRaisesRegex(RuntimeError, "must end in .html"):
            site_model.route_to_output("/modules/07-concurrency-lifecycle-failure")

    def test_readme_rewrites(self) -> None:
        self.assertEqual(site_model.path_to_rewrite("README.md"), "index.md")
        self.assertEqual(
            site_model.path_to_rewrite("practicum/README.md"), "practicum/index.md"
        )
        self.assertIsNone(site_model.path_to_rewrite("extensions/index.md"))

    def test_site_base_is_normalized(self) -> None:
        with patch.dict(os.environ, {"COURSE_SITE_BASE": "/agent-se/"}):
            self.assertEqual(site_model.site_base(), "/agent-se/")
            self.assertEqual(
                site_model.route_with_base("/modules/m07"), "/agent-se/modules/m07"
            )
        with patch.dict(os.environ, {"COURSE_SITE_BASE": "/"}):
            self.assertEqual(site_model.route_with_base("/modules/m07"), "/modules/m07")

    def test_student_model_uses_canonical_graph(self) -> None:
        model = site_model.build_site_model("student")
        pages = {page["id"]: page for page in model["pages"]}
        excluded = {page["id"]: page for page in model["excluded_canonical"]}

        self.assertEqual(len(pages), 54)
        self.assertEqual([page["order"] for page in model["main_path"]], list(range(15)))
        self.assertEqual(model["main_path"][-1]["id"], "final-practicum")
        self.assertNotIn("case-M07", pages)
        self.assertIn("case-M07", excluded)
        self.assertNotIn("source-M13", pages)
        self.assertIn("source-M13", excluded)
        self.assertIn("MATERIALS_REVIEW.md", model["src_exclude"])
        self.assertIn("case-studies/m07/instructor-analysis.md", model["src_exclude"])
        self.assertIn("site/**", model["src_exclude"])
        self.assertEqual(model["rewrites"]["README.md"], "index.md")
        self.assertEqual(model["rewrites"]["practicum/README.md"], "practicum/index.md")

    def test_instructor_and_all_visibility(self) -> None:
        instructor = site_model.build_site_model("instructor")
        all_pages = site_model.build_site_model("all")
        instructor_ids = {page["id"] for page in instructor["pages"]}
        all_ids = {page["id"] for page in all_pages["pages"]}

        self.assertEqual(len(instructor["pages"]), 68)
        self.assertEqual(len(all_pages["pages"]), 71)
        self.assertIn("case-M07", instructor_ids)
        self.assertNotIn("materials-review", instructor_ids)
        self.assertTrue({"case-M07", "source-M13"}.issubset(instructor_ids))
        self.assertTrue(all_ids.issuperset(instructor_ids))
        self.assertEqual(
            {page["visibility"] for page in all_pages["pages"]},
            {"student", "instructor", "internal"},
        )

    def test_output_verifier_rejects_unexpected_html(self) -> None:
        model = {
            "visibility": "student",
            "pages": [{"route": "/"}, {"route": "/modules/m00.html"}],
            "excluded_canonical": [{"route": "/hidden.html"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            dist = root / "dist"
            (dist / "modules").mkdir(parents=True)
            (dist / "assets/chunks").mkdir(parents=True)
            (dist / "index.html").write_text("home", encoding="utf-8")
            (dist / "modules/m00.html").write_text("m00", encoding="utf-8")
            (dist / "extra.html").write_text("extra", encoding="utf-8")
            (dist / "assets/chunks/@localSearchIndexroot.test.js").write_text(
                "export default '{}'", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "non-canonical Markdown routes"):
                site_model.verify_output("student", dist, model_path)

    def test_output_verifier_rejects_hidden_search_route(self) -> None:
        model = {
            "visibility": "student",
            "pages": [{"route": "/"}],
            "excluded_canonical": [{"route": "/hidden.html"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            dist = root / "dist"
            (dist / "assets/chunks").mkdir(parents=True)
            (dist / "index.html").write_text("home", encoding="utf-8")
            (dist / "assets/chunks/@localSearchIndexroot.test.js").write_text(
                "export default '/hidden.html'", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "search index contains excluded"):
                site_model.verify_output("student", dist, model_path)


if __name__ == "__main__":
    unittest.main()
