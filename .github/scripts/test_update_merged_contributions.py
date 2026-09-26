"""Offline contract tests; all API payloads below are synthetic fixtures."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("updater", Path(__file__).with_name("update_merged_contributions.py"))
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
CODE_URL = "https://github.com/toss/react-simplikit/pull/473"
DOC_URL = "https://github.com/lodash/lodash/pull/6196"


def detail(url=CODE_URL, merged=True):
    repo, number = url.removeprefix("https://github.com/").split("/pull/")
    return {
        "html_url": url, "number": int(number), "title": "Synthetic fixture",
        "merged_at": "2026-01-01T00:00:00Z" if merged else None,
        "user": {"login": "JetProc"},
        "base": {"repo": {"full_name": repo, "html_url": f"https://github.com/{repo}", "private": False, "archived": False}},
    }


def normalize(details, **kwargs):
    with patch.object(m, "load_pull_request_details", side_effect=details):
        return m.normalize_pull_requests([{} for _ in details], "JetProc", kwargs.get("owners", set()), kwargs.get("limit", 12), None, kwargs.get("repos", set()))


class ContributionsTests(unittest.TestCase):
    def test_catalog_categories_are_valid(self):
        self.assertEqual({category for category, _ in m.CONTRIBUTIONS.values()}, {"code", "docs"})

    def test_two_groups(self):
        rendered = m.render_rows(normalize([detail(), detail(DOC_URL)]))
        self.assertIn("### Code Contributions", rendered)
        self.assertIn("### Documentation / Community", rendered)
        code, docs = rendered.split("### Documentation / Community")
        self.assertIn(CODE_URL, code)
        self.assertNotIn(DOC_URL, code)
        self.assertIn(DOC_URL, docs)
        self.assertNotIn(CODE_URL, docs)

    def test_open_pr_is_not_a_merged_contribution(self):
        self.assertEqual(normalize([detail(merged=False)]), [])

    def test_different_author_excluded(self):
        value = detail()
        value["user"]["login"] = "SomeoneElse"
        self.assertEqual(normalize([value]), [])

    def test_private_repo_excluded(self):
        value = detail()
        value["base"]["repo"]["private"] = True
        self.assertEqual(normalize([value]), [])

    def test_archived_repo_excluded(self):
        value = detail()
        value["base"]["repo"]["archived"] = True
        self.assertEqual(normalize([value]), [])

    def test_own_repo_excluded(self):
        value = detail()
        value["base"]["repo"]["full_name"] = "JetProc/example"
        self.assertEqual(normalize([value]), [])

    def test_excluded_owner(self):
        self.assertEqual(normalize([detail()], owners={"toss"}), [])

    def test_excluded_repo_case_insensitive(self):
        self.assertEqual(normalize([detail()], repos={"toss/react-simplikit"}), [])

    def test_unclassified_pr_requires_review(self):
        with patch("sys.stderr"):
            self.assertEqual(normalize([detail("https://github.com/example/project/pull/1")]), [])

    def test_duplicate_removed(self):
        self.assertEqual(len(normalize([detail(), detail()])), 1)

    def test_sort_before_limit(self):
        older, newer = detail(), detail(DOC_URL)
        newer["merged_at"] = "2026-02-01T00:00:00Z"
        self.assertEqual(normalize([older, newer], limit=1)[0]["url"], DOC_URL)

    def test_empty_group_label_not_dropped(self):
        rendered = m.render_rows(normalize([detail()]))
        self.assertIn("### Documentation / Community", rendered)
        self.assertIn("병합이 확인된 기여가 없습니다", rendered)

    def test_surrounding_readme_unchanged_and_idempotent(self):
        before = "INTRO\n" + m.START_MARKER + "\nold\n" + m.END_MARKER + "\nSKILLS\n2024.06–2026.01\n"
        rendered = m.render_rows(normalize([detail()]))
        after = m.replace_marker_block(before, rendered)
        self.assertTrue(after.startswith("INTRO\n"))
        self.assertTrue(after.endswith("\nSKILLS\n2024.06–2026.01\n"))
        self.assertEqual(after, m.replace_marker_block(after, rendered))

    def test_backslashes_and_markdown_are_literal(self):
        escaped = m.escape_markdown("fix[isNumber] | \\1\nline")
        text = m.replace_marker_block(m.START_MARKER + m.END_MARKER, escaped)
        self.assertIn(escaped, text)
        self.assertNotIn("\nline", escaped)
        self.assertIn("\\|", escaped)

    def test_bad_markers_fail_closed(self):
        samples = ["none", m.START_MARKER, m.END_MARKER + m.START_MARKER,
                   m.START_MARKER * 2 + m.END_MARKER, m.START_MARKER + m.END_MARKER * 2]
        for sample in samples:
            with self.subTest(sample=sample), self.assertRaises(RuntimeError):
                m.replace_marker_block(sample, "replacement")

    def test_incomplete_search_fails(self):
        with patch.object(m, "request_json", return_value={"items": [], "incomplete_results": True}):
            with self.assertRaises(RuntimeError):
                m.search_merged_pull_requests("JetProc", set(), 60, None)

    def test_truncated_search_requires_pagination(self):
        with patch.object(m, "request_json", return_value={"items": [], "total_count": 61}):
            with self.assertRaises(RuntimeError):
                m.search_merged_pull_requests("JetProc", set(), 60, None)

    def test_token_not_sent_to_foreign_host(self):
        with patch.object(m, "urlopen") as request:
            with self.assertRaises(RuntimeError):
                m.request_json("https://api.github.com.example.com/steal", "test-token")
            request.assert_not_called()

    def test_api_failure_preserves_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            original = "prefix\n" + m.START_MARKER + "\nknown\n" + m.END_MARKER
            path.write_text(original)
            with patch.dict(os.environ, {"GITHUB_USERNAME": "JetProc", "README_PATH": str(path)}):
                with patch.object(m, "search_merged_pull_requests", side_effect=RuntimeError("API failure")):
                    with self.assertRaises(RuntimeError):
                        m.main()
            self.assertEqual(path.read_text(), original)

    def test_zero_verified_rows_preserves_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            original = m.START_MARKER + "known" + m.END_MARKER
            path.write_text(original)
            with patch.dict(os.environ, {"GITHUB_USERNAME": "JetProc", "README_PATH": str(path)}):
                with patch.object(m, "search_merged_pull_requests", return_value=[]):
                    with self.assertRaises(RuntimeError):
                        m.main()
            self.assertEqual(path.read_text(), original)

    def test_invalid_limits_use_defaults(self):
        for value in ["0", "-1", "invalid"]:
            with patch.dict(os.environ, {"MAX_ITEMS": value}):
                self.assertEqual(m.env_int("MAX_ITEMS", 12), 12)


if __name__ == "__main__":
    unittest.main()
