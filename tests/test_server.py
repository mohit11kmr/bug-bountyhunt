"""Unit tests for gui/server.py — stdlib unittest only, no new dependency.

Run: python3 -m unittest discover -s tests -v

Every test that touches persisted state (watchlist, sessions, findings
status) redirects the module's path constants to a temp directory for the
duration of the test and restores them afterward, so running these tests
never mutates real workspace/engagement data on disk.
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_server_module():
    spec = importlib.util.spec_from_file_location("bg_gui_server", ROOT / "gui" / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = _load_server_module()


class ScopeTableParsingTests(unittest.TestCase):
    def test_parses_target_type_notes_rows(self):
        text = (
            "# Security Agent — Test\n\n"
            "## ✅ IN Scope\n\n"
            "| Target | Type | Notes |\n"
            "|---|---|---|\n"
            "| example.com | URL | staging only |\n"
            "| api.example.com | URL | |\n\n"
            "## Next Section\n"
            "should not be included\n"
        )
        targets = server._parse_scope_table(text)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0]["target"], "example.com")
        self.assertEqual(targets[0]["notes"], "staging only")
        self.assertEqual(targets[1]["target"], "api.example.com")

    def test_no_scope_heading_returns_empty(self):
        self.assertEqual(server._parse_scope_table("# nothing here"), [])

    def test_skips_header_and_separator_rows(self):
        text = "## IN Scope\n| Target | Type | Notes |\n|---|---|---|\n"
        self.assertEqual(server._parse_scope_table(text), [])


class LoadJsonTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        self.assertIsNone(server._load_json(ROOT / "tests" / "does-not-exist.json"))

    def test_malformed_json_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text("{not valid json")
            self.assertIsNone(server._load_json(p))

    def test_valid_json_returns_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "good.json"
            p.write_text(json.dumps({"a": 1}))
            self.assertEqual(server._load_json(p), {"a": 1})


class WatchlistTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_path = server.WATCHLIST_PATH
        server.WATCHLIST_PATH = Path(self._tmpdir.name) / "watchlist.json"

    def tearDown(self):
        server.WATCHLIST_PATH = self._orig_path
        self._tmpdir.cleanup()

    def test_add_then_list(self):
        entry, err = server.add_to_watchlist("mozilla", "Mozilla")
        self.assertIsNone(err)
        self.assertEqual(entry["handle"], "mozilla")
        self.assertEqual(server._read_watchlist(), [entry])

    def test_add_is_idempotent(self):
        first, _ = server.add_to_watchlist("mozilla", "Mozilla")
        second, err = server.add_to_watchlist("mozilla", "Mozilla (renamed)")
        self.assertIsNone(err)
        self.assertEqual(first, second)
        self.assertEqual(len(server._read_watchlist()), 1)

    def test_invalid_handle_rejected(self):
        entry, err = server.add_to_watchlist("not a valid handle!", "x")
        self.assertIsNone(entry)
        self.assertIsNotNone(err)

    def test_remove_existing(self):
        server.add_to_watchlist("mozilla", "Mozilla")
        ok, err = server.remove_from_watchlist("mozilla")
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(server._read_watchlist(), [])

    def test_remove_nonexistent_fails_cleanly(self):
        ok, err = server.remove_from_watchlist("never-tracked")
        self.assertFalse(ok)
        self.assertIsNotNone(err)


class ReadSessionsDiscriminationTests(unittest.TestCase):
    """Regression test for the fix in read_sessions(): only hunt-*.json
    files (hunt.md's Step 10 output) should be parsed as hunt sessions.
    A manual /session-save file (name/saved_at/scope/tested_urls/findings)
    living in the same sessions/ directory must not be picked up — it has
    no validated_findings/hunters_launched keys and would otherwise render
    as a phantom, null-target session card."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_root = server.ROOT
        server.ROOT = Path(self._tmpdir.name)
        (server.ROOT / "sessions").mkdir()

    def tearDown(self):
        server.ROOT = self._orig_root
        self._tmpdir.cleanup()

    def _write_session(self, filename, data):
        (server.ROOT / "sessions" / filename).write_text(json.dumps(data))

    def test_hunt_session_is_read(self):
        self._write_session("hunt-example.com-2026-09-04.json", {
            "target": "example.com", "program": "mozilla", "date": "2026-09-04",
            "hunters_launched": "17/17", "endpoints_discovered": 3,
            "summary": "test", "validated_findings": [], "discarded": [],
            "bounty_eligible": None, "suggested_action": None,
        })
        programs = {}
        server.read_sessions(programs)
        self.assertIn("mozilla", programs)
        self.assertEqual(len(programs["mozilla"]["sessions"]), 1)
        self.assertEqual(programs["mozilla"]["sessions"][0]["target"], "example.com")

    def test_manual_audit_session_is_excluded(self):
        self._write_session("my-checkpoint.json", {
            "name": "my-checkpoint", "program": "mozilla",
            "saved_at": "2026-09-04T00:00:00Z", "scope": ["example.com"],
            "tested_urls": [], "findings": [], "notes": "",
        })
        programs = {}
        server.read_sessions(programs)
        self.assertNotIn("mozilla", programs)

    def test_both_present_only_hunt_session_read(self):
        self._write_session("hunt-example.com-2026-09-04.json", {
            "target": "example.com", "program": "mozilla", "date": "2026-09-04",
            "hunters_launched": "17/17", "endpoints_discovered": 3,
            "summary": "test", "validated_findings": [], "discarded": [],
            "bounty_eligible": None, "suggested_action": None,
        })
        self._write_session("my-checkpoint.json", {
            "name": "my-checkpoint", "program": "mozilla",
            "saved_at": "2026-09-04T00:00:00Z", "scope": [], "tested_urls": [],
            "findings": [], "notes": "",
        })
        programs = {}
        server.read_sessions(programs)
        self.assertEqual(len(programs["mozilla"]["sessions"]), 1)
        self.assertEqual(
            programs["mozilla"]["sessions"][0]["file"],
            "hunt-example.com-2026-09-04.json",
        )


if __name__ == "__main__":
    unittest.main()
