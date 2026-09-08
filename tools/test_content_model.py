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

    def test_setext_heading_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\nSecond title\n============\n")
        self.assertTrue(any("Setext headings are not allowed" in error for error in self.errors()))

    def test_indented_atx_heading_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n  # Accidental second H1\n")
        self.assertTrue(any("indented ATX headings are not allowed" in error for error in self.errors()))

    def test_tab_indented_atx_heading_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n\t## Hidden heading\n")
        self.assertTrue(any("indented ATX headings are not allowed" in error for error in self.errors()))

    def test_container_heading_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n> # Hidden H1\n")
        self.assertTrue(any("headings inside blockquote/list containers are not allowed" in error for error in self.errors()))

    def test_list_continuation_heading_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n- item  \n  ## Hidden heading\n")
        self.assertTrue(any("indented ATX headings are not allowed" in error for error in self.errors()))

    def test_closing_atx_hash_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n## Heading with closer #\n")
        self.assertTrue(any("closing ATX heading hashes are not allowed" in error for error in self.errors()))

    def test_mismatched_inline_backticks_cannot_hide_visibility_link(self) -> None:
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n`[spoiler](../case-studies/m07/./instructor.md)``\n")
        errors = self.errors()
        self.assertTrue(any("inline code supports only paired single backticks" in error for error in errors))
        self.assertTrue(any("outside its build visibility" in error for error in errors))

    def test_escaped_backticks_cannot_hide_visibility_link(self) -> None:
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(r"\`[spoiler](../case-studies/m07/./instructor.md)\`" + "\n")
        errors = self.errors()
        self.assertTrue(any("backslash-escaped backticks are not allowed" in error for error in errors))
        self.assertTrue(any("outside its build visibility" in error for error in errors))

    def test_four_space_fake_fence_cannot_hide_visibility_link(self) -> None:
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n    ```\n"
                "[spoiler](../case-studies/m07/./instructor.md)\n"
                "```\n"
            )
        errors = self.errors()
        self.assertTrue(any("indented four or more spaces" in error for error in errors))
        self.assertTrue(any("outside its build visibility" in error for error in errors))

    def test_invalid_backtick_fence_info_cannot_hide_visibility_link(self) -> None:
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n```foo`bar\n"
                "[spoiler](../case-studies/m07/./instructor.md)\n"
                "```\n"
            )
        errors = self.errors()
        self.assertTrue(any("fence info string may not contain" in error for error in errors))
        self.assertTrue(any("outside its build visibility" in error for error in errors))

    def test_double_backtick_inline_code_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n``literal``\n")
        self.assertTrue(any("inline code supports only paired single backticks" in error for error in self.errors()))

    def test_four_backtick_fence_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n````text\nliteral\n````\n")
        self.assertTrue(any("exactly three backticks or tildes" in error for error in self.errors()))

    def test_unclosed_supported_fence_is_rejected(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n```text\nliteral\n")
        self.assertTrue(any("unclosed fenced code block" in error for error in self.errors()))

    def test_three_space_triple_fence_is_supported(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n   ```text\n"
                "[literal](../labs/does-not-exist.md)\n"
                "   ```\n"
            )
        self.assertEqual(self.errors(), [])

    def test_processing_instruction_and_cdata_are_rejected_as_raw_html(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n<?pi data?>\n<![CDATA[data]]>\n")
        errors = self.errors()
        self.assertGreaterEqual(sum("raw HTML is not allowed" in error for error in errors), 2)

    def test_supported_inline_code_and_triple_fence_hide_literal_links(self) -> None:
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n`[literal](../labs/does-not-exist.md)`\n"
                "```text\n"
                "[literal](../labs/does-not-exist.md)\n"
                "```\n"
            )
        self.assertEqual(self.errors(), [])

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

    def test_reference_style_link_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n[missing][x]\n\n[x]: ../labs/does-not-exist.md\n")
        self.assertTrue(any("reference-style links are not allowed" in error for error in self.errors()))

    def test_reference_style_visibility_bypass_is_rejected(self) -> None:
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        path = self.root / "modules/07-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n[spoiler][hidden-case]\n\n"
                "[hidden-case]: ../case-studies/m07/%69nstructor.md\n"
            )
        self.assertTrue(any("reference-style links are not allowed" in error for error in self.errors()))

    def test_raw_html_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n<a href=\"../labs/does-not-exist.md\">missing</a>\n")
        self.assertTrue(any("raw HTML is not allowed" in error for error in self.errors()))

    def test_angle_autolink_is_rejected_as_unsupported_markdown(self) -> None:
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\nSee <https://example.com/source>.\n")
        self.assertTrue(any("angle-bracket autolinks are not allowed" in error for error in self.errors()))

    def test_complex_inline_link_syntax_is_rejected(self) -> None:
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n[nested [label]](../labs/05-lab.md)\n")
        self.assertTrue(any("unsupported inline link/image syntax" in error for error in self.errors()))

    def test_local_link_may_not_escape_repository_root(self) -> None:
        outside = self.root.parent / "outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        path = self.root / "modules/05-module.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[escape](../../{outside.name})\n")
        self.assertTrue(any("escapes repository root" in error for error in self.errors()))

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

    def test_top_level_lab_without_frontmatter_is_rejected(self) -> None:
        path = self.root / "labs/supplement.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Supplement\n", encoding="utf-8")
        self.assertTrue(any("required canonical content page has no frontmatter" in error for error in self.errors()))

    def test_nested_practicum_repo_artifact_is_not_promoted(self) -> None:
        path = self.root / "practicum/raw-notes/README.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Repo-only notes\n", encoding="utf-8")
        self.assertEqual(self.errors(), [])

    def test_manifest_visibility_and_inverse_relations(self) -> None:
        self.write_page(
            "labs/07-lab.md",
            page_id="lab-M07",
            page_type="lab",
            visibility="student",
            title="Lab M07",
            related=("M07",),
        )
        self.write_page(
            "case-studies/m07/instructor.md",
            page_id="case-M07",
            page_type="case_study",
            visibility="instructor",
            title="Instructor Case",
            related=("M07",),
        )
        self.write_page(
            "reading-notes/internal.md",
            page_id="internal-record",
            page_type="reference",
            visibility="internal",
            title="Internal Record",
            related=("M07",),
        )

        pages, errors = content_model.validate()
        self.assertEqual(errors, [])

        student = content_model.manifest(pages, "student")
        instructor = content_model.manifest(pages, "instructor")
        all_pages = content_model.manifest(pages, "all")

        student_by_id = {page["id"]: page for page in student["pages"]}
        instructor_by_id = {page["id"]: page for page in instructor["pages"]}
        all_by_id = {page["id"]: page for page in all_pages["pages"]}

        self.assertIn("lab-M07", student_by_id)
        self.assertNotIn("case-M07", student_by_id)
        self.assertNotIn("internal-record", student_by_id)
        self.assertEqual(student_by_id["M07"]["related_by"], ["lab-M07"])

        self.assertIn("case-M07", instructor_by_id)
        self.assertNotIn("internal-record", instructor_by_id)
        self.assertEqual(
            instructor_by_id["M07"]["related_by"],
            ["case-M07", "lab-M07"],
        )

        self.assertIn("internal-record", all_by_id)
        self.assertEqual(
            all_by_id["M07"]["related_by"],
            ["case-M07", "internal-record", "lab-M07"],
        )


if __name__ == "__main__":
    unittest.main()
