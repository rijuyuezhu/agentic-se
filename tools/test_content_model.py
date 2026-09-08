#!/usr/bin/env python3
"""Regression tests for the canonical content-model validator."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import content_model


class ContentModelValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.original_root = content_model.ROOT
        content_model.ROOT = self.root

        for order in range(14):
            module_id = f"M{order:02d}"
            self.write_page(
                f"modules/{order:02d}-module.md",
                page_id=module_id,
                page_type="module",
                visibility="student",
                order=order,
                title=module_id,
            )
        self.write_page(
            "practicum/README.md",
            page_id="final-practicum",
            page_type="practicum",
            visibility="student",
            order=14,
            title="Final Practicum",
        )

    def tearDown(self) -> None:
        content_model.ROOT = self.original_root
        self.tempdir.cleanup()

    def write_page(
        self,
        relpath: str,
        *,
        page_id: str,
        page_type: str,
        visibility: str,
        title: str,
        order: int | None = None,
        related: tuple[str, ...] = (),
        body: str = "",
    ) -> Path:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "---",
            f"id: {page_id}",
            f"type: {page_type}",
            f"visibility: {visibility}",
        ]
        if order is not None:
            fields.append(f"order: {order}")
        if related:
            fields.append(f"related: [{', '.join(related)}]")
        fields.extend(["---", f"# {title}"])
        if body:
            fields.extend(["", body])
        path.write_text("\n".join(fields) + "\n", encoding="utf-8")
        return path

    def errors(self) -> list[str]:
        return content_model.validate()[1]

    def test_minimal_main_path_is_valid(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_duplicate_id_is_rejected(self) -> None:
        self.write_page(
            "extensions/duplicate.md",
            page_id="M00",
            page_type="extension",
            visibility="student",
            title="Duplicate",
        )
        self.assertTrue(any("duplicate content id" in error for error in self.errors()))

    def test_unknown_relation_is_rejected(self) -> None:
        self.write_page(
            "labs/02-lab.md",
            page_id="lab-M02",
            page_type="lab",
            visibility="student",
            title="Lab",
            related=("does-not-exist",),
        )
        self.assertTrue(any("related references unknown id" in error for error in self.errors()))

    def test_second_h1_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n# Accidental second H1\n", encoding="utf-8")
        self.assertTrue(any("exactly one semantic H1" in error for error in self.errors()))

    def test_source_audit_requires_review_date(self) -> None:
        self.write_page(
            "reading-notes/m07-source-audit.md",
            page_id="source-M07",
            page_type="source_audit",
            visibility="student",
            title="Source Audit",
            related=("M07",),
        )
        self.assertTrue(any("must record an audit/review/freshness date" in error for error in self.errors()))

    def test_bare_external_url_is_rejected(self) -> None:
        path = self.root / "modules/06-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\nSee https://example.com/source for details.\n")
        self.assertTrue(any("bare external URL in prose" in error for error in self.errors()))

    def test_broken_local_link_is_rejected(self) -> None:
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n[missing](../labs/does-not-exist.md)\n")
        self.assertTrue(any("broken local Markdown link" in error for error in self.errors()))

    def test_visibility_lattice_rejects_hidden_links(self) -> None:
        instructor = self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        student = self.root / "modules/07-module.md"
        with student.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n[spoiler]({Path(os.path.relpath(instructor, student.parent)).as_posix()})\n"
            )
        self.assertTrue(any("outside its build visibility" in error for error in self.errors()))

    def test_instructor_cannot_link_internal_page(self) -> None:
        internal = self.write_page(
            "reading-notes/internal.md",
            page_id="internal-record",
            page_type="reference",
            visibility="internal",
            title="Internal Record",
        )
        instructor = self.write_page(
            "case-studies/m08/instructor.md",
            page_id="case-M08",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M08",),
        )
        with instructor.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n[internal]({Path(os.path.relpath(internal, instructor.parent)).as_posix()})\n"
            )
        self.assertTrue(any("outside its build visibility" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
