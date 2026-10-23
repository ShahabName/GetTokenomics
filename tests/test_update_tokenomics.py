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
                "# Global Instructions\n- **Tokenomics Tracking Switch**: `TOKENOMICS_SWITCH: ON`\n",
                encoding="utf-8",
            )
            enabled, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertTrue(enabled)

            ut.set_tokenomics_switch(False, str(inst))
            enabled_after_off, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertFalse(enabled_after_off)

            ut.set_tokenomics_switch(True, str(inst))
            enabled_after_on, _ = ut.is_tokenomics_enabled(str(inst))
            self.assertTrue(enabled_after_on)

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


if __name__ == "__main__":
    unittest.main()
