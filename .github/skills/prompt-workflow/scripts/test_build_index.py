"""Tests for build_index.py. Run: python3 -m unittest discover -s .github/skills/prompt-workflow/scripts"""

import importlib.util
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "build_index", Path(__file__).with_name("build_index.py")
)
build_index = importlib.util.module_from_spec(_spec)
sys.modules["build_index"] = build_index
_spec.loader.exec_module(build_index)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip())


class BuildIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.prompts = self.root / ".github" / "prompts"
        self.prompts.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def readme(self, prompts_dir=None) -> str:
        return ((prompts_dir or self.prompts) / "README.md").read_text()

    def test_groups_by_status_in_fixed_order(self):
        write(self.prompts / "2026-01-01_0900_old.md", "---\nstatus: done\n---\n# Old work\n")
        write(self.prompts / "2026-02-01_0900_wip.md", "---\nstatus: in-progress\n---\n# Busy\n")
        write(self.prompts / "2026-03-01_0900_new.md", "---\nstatus: open\n---\n# Fresh\n")
        write(self.prompts / "backlog.md", "---\nstatus: reference\n---\n# Backlog\n")
        write(self.prompts / "2026-01-15_0900_later.md", "---\nstatus: parked\n---\n# Later\n")
        build_index.build(self.root)
        text = self.readme()
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        self.assertEqual(
            headings,
            ["## In progress (1)", "## Open (1)", "## Parked (1)", "## Reference (1)", "## Done (1)"],
        )
        self.assertLess(text.index("Busy"), text.index("Fresh"))
        self.assertLess(text.index("Later"), text.index("Backlog"))

    def test_newest_first_within_a_group(self):
        write(self.prompts / "2026-01-01_0900_a.md", "---\nstatus: done\n---\n# First\n")
        write(self.prompts / "2026-05-01_0900_b.md", "---\nstatus: done\n---\n# Second\n")
        build_index.build(self.root)
        text = self.readme()
        self.assertLess(text.index("Second"), text.index("First"))

    def test_missing_or_invalid_status_listed_and_fails_check(self):
        write(self.prompts / "2026-01-01_0900_plain.md", "# No front matter\n")
        write(self.prompts / "2026-01-02_0900_bad.md", "---\nstatus: finished\n---\n# Bad status\n")
        build_index.build(self.root)
        self.assertIn("## No status (2)", self.readme())
        problems = build_index.check(self.root)
        self.assertEqual(len([p for p in problems if "status" in p]), 2)

    def test_title_from_first_heading_outside_fences_else_readable_file_name(self):
        write(
            self.prompts / "2026-01-01_0900_fenced.md",
            """
            ---
            status: open
            ---
            ```
            # not a title
            ```
            # Real title
            """,
        )
        write(self.prompts / "2026-01-02_0900_pending-budget_changes.md", "---\nstatus: open\n---\nno heading\n")
        write(self.prompts / "2026-01-03_ToDo.md", "---\nstatus: open\n---\n")
        write(self.prompts / "generate_rename.prompt.md", "---\nstatus: reference\n---\n")
        build_index.build(self.root)
        text = self.readme()
        self.assertIn("[Real title]", text)
        self.assertNotIn("not a title", text)
        self.assertIn("[pending budget changes]", text)
        self.assertIn("[ToDo]", text)
        self.assertIn("[generate rename]", text)

    def test_counts_only_empty_answer_lines_in_clarifications(self):
        write(
            self.prompts / "2026-01-01_0900_q.md",
            """
            ---
            status: open
            ---
            # Questions

            ## Plan

               >

            ```markdown
            ## Clarifications
               >
            ```

            ## Clarifications

            1. **One?**

               > a

            2. **Two?**

               >

            3. **Three?**

               >

            ## Work log

               >
            """,
        )
        info = build_index.parse(self.prompts / "2026-01-01_0900_q.md")
        self.assertEqual(info.open_clarifications, 2)

    def test_existing_front_matter_keys_are_kept_and_comments_ignored(self):
        write(
            self.prompts / "tool.prompt.md",
            "---\nmode: agent\ndescription: x\nstatus: reference  # living doc\n---\n# Tool\n",
        )
        self.assertEqual(build_index.parse(self.prompts / "tool.prompt.md").status, "reference")

    def test_date_column_and_url_encoded_links(self):
        write(self.prompts / "2026-10-10_2107_has time.md", "---\nstatus: open\n---\n# T | pipe\n")
        write(self.prompts / "2026-10-11_dateonly.md", "---\nstatus: open\n---\n# D\n")
        build_index.build(self.root)
        text = self.readme()
        self.assertIn("| 2026-10-10 21:07 | [T \\| pipe](2026-10-10_2107_has%20time.md) |", text)
        self.assertIn("| 2026-10-11 | [D](2026-10-11_dateonly.md) |", text)

    def test_readme_and_non_markdown_files_are_ignored(self):
        write(self.prompts / "notes.txt", "x")
        write(self.prompts / "2026-01-01_0900_a.md", "---\nstatus: done\n---\n# A\n")
        build_index.build(self.root)
        build_index.build(self.root)
        text = self.readme()
        self.assertNotIn("notes.txt", text)
        self.assertNotIn("[Prompt files]", text)
        self.assertIn("## Done (1)", text)

    def test_idempotent_and_check_detects_stale_readme(self):
        write(self.prompts / "2026-01-01_0900_a.md", "---\nstatus: open\n---\n# A\n")
        build_index.build(self.root)
        first = self.readme()
        build_index.build(self.root)
        self.assertEqual(first, self.readme())
        self.assertEqual(build_index.check(self.root), [])
        write(self.prompts / "2026-01-01_0900_a.md", "---\nstatus: done\n---\n# A\n")
        self.assertTrue(any("README.md" in p for p in build_index.check(self.root)))

    def test_check_reports_missing_readme(self):
        write(self.prompts / "2026-01-01_0900_a.md", "---\nstatus: open\n---\n# A\n")
        self.assertTrue(any("README.md" in p for p in build_index.check(self.root)))

    def test_empty_prompts_dir_gets_placeholder(self):
        build_index.build(self.root)
        self.assertIn("No prompt files yet", self.readme())

    def test_finds_subproject_prompt_dirs_and_skips_vendored_dirs(self):
        sub = self.root / "EXIF" / ".github" / "prompts"
        write(sub / "2026-01-01_0900_s.md", "---\nstatus: done\n---\n# Sub\n")
        write(self.root / "node_modules" / "x" / ".github" / "prompts" / "y.md", "# vendored\n")
        write(self.root / ".venv" / "lib" / ".github" / "prompts" / "z.md", "# venv\n")
        dirs = build_index.find_prompt_dirs(self.root)
        self.assertEqual(dirs, [self.prompts, sub])
        build_index.build(self.root)
        self.assertIn("[Sub]", self.readme(sub))
        self.assertFalse((self.root / "node_modules" / "x" / ".github" / "prompts" / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
