import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "update-tokenomics.py"
spec = importlib.util.spec_from_file_location("update_tokenomics", MODULE_PATH)
assert spec and spec.loader
ut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ut)


class TestGetTokenomics(unittest.TestCase):
    def test_headers_count_is_29(self):
        self.assertEqual(len(ut.HEADERS), 29)
        self.assertEqual(ut.HEADERS[0], "timestamp_utc")
        self.assertEqual(ut.HEADERS[-1], "prompt_summary")

    def test_switch_toggle_on_and_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            inst = Path(tmp) / "global.instructions.md"
            inst.write_text(
                "# Global Instructions\n- **Tokenomics Tracking Switch**: `TOKENOMICS_SWITCH: OFF`\n",
                encoding="utf-8",
            )
            enabled, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertFalse(enabled)

            ut.set_tokenomics_switch(True, str(inst))
            enabled_after_on, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertTrue(enabled_after_on)

            ut.set_tokenomics_switch(False, str(inst))
            enabled_after_off, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertFalse(enabled_after_off)

    def test_parse_and_update_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_root = tmp_path / "session-state"
            sid = "test-session-1234"
            session_dir = state_root / sid
            session_dir.mkdir(parents=True)
            events_file = session_dir / "events.jsonl"

            events = [
                {
                    "type": "user.message",
                    "timestamp": "2026-10-24T10:00:00.000Z",
                    "data": {
                        "content": "<current_datetime>2026-10-24</current_datetime>\nSolve Challenge 7 testing framework"
                    },
                },
                {
                    "type": "session.usage_record",
                    "timestamp": "2026-10-24T10:00:05.000Z",
                    "data": {
                        "usage": {
                            "initiator": "user",
                            "model": "gpt-5.3-codex",
                            "modelDisplayName": "GPT-5.3 Codex",
                            "reasoningEffort": "high",
                            "cost": 1.0,
                            "inputTokens": 10000,
                            "cacheReadTokens": 9000,
                            "cacheWriteTokens": 0,
                            "outputTokens": 500,
                            "reasoningTokens": 200,
                            "toolTokenCount": 5000,
                            "duration": 4500,
                            "timeToFirstTokenMs": 850.4,
                            "toolCounts": {"view": 2, "edit": 1},
                            "finishReason": "stop",
                            "aiCreditsStatus": "complete",
                            "accounting": {"sequence": 1},
                            "copilotUsage": {
                                "totalNanoAiu": 2500000000,
                                "tokenDetails": [{"tokenType": "input", "tokenCount": 1000}],
                            },
                        }
                    },
                },
            ]
            with events_file.open("w", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev) + "\n")

            csv_path = tmp_path / "tokenomics-20261024.csv"
            all_rows, latest_rows = ut.update_csv(csv_path, [sid], state_root)
            self.assertEqual(len(all_rows), 1)
            self.assertEqual(len(latest_rows), 1)
            row = latest_rows[0]
            self.assertEqual(row["challenge_or_task"], "C7-Task")
            self.assertEqual(row["cache_hit_ratio_pct"], "90.00")
            self.assertEqual(row["total_aiu_credits"], "2.500000")
            self.assertEqual(row["tools_invoked"], "edit:1;view:2")

            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, ut.HEADERS)

    def test_given_repo_and_website_snippets_when_inspected_then_default_off_and_preserve_output_rule_are_present(self):
        repo_root = Path(__file__).resolve().parent.parent
        heading = "## Preserve default VS Code chat output"
        bullet_one = "Recording tokenomics (`update-tokenomics.py`) and appending `## Tokenomics` and `## Files` are strictly additive and must **never** replace, suppress, or alter VS Code's normal chat response or built-in tool defaults."
        bullet_one_js = r"Recording tokenomics (\`update-tokenomics.py\`) and appending \`## Tokenomics\` and \`## Files\` are strictly additive and must **never** replace, suppress, or alter VS Code's normal chat response or built-in tool defaults."
        bullet_two = "Always display the complete user-facing explanation, analysis, or report in the chat response"
        markdown_files = [
            repo_root / "instructions" / "global-instructions-snippet.md",
            repo_root / "instructions" / "tokenomics.instructions.md",
            repo_root / "README.md",
            repo_root / "LINKEDIN_ARTICLE.md",
            repo_root / "linkedin" / "LINKEDIN_ARTICLE.md",
        ]
        html_file = repo_root / "docs" / "index.html"

        for md_path in markdown_files:
            content = md_path.read_text(encoding="utf-8")
            self.assertIn(heading, content, f"Missing heading in {md_path}")
            self.assertIn(bullet_one, content, f"Missing first bullet in {md_path}")
            self.assertIn(bullet_two, content, f"Missing second bullet in {md_path}")
            self.assertIn("TOKENOMICS_SWITCH: OFF", content, f"Default OFF switch missing in {md_path}")

        html_content = html_file.read_text(encoding="utf-8")
        self.assertEqual(html_content.count(heading), 2)
        self.assertIn(bullet_one, html_content)
        self.assertIn(bullet_one_js, html_content)
        self.assertEqual(html_content.count(bullet_two), 2)


if __name__ == "__main__":
    unittest.main()
