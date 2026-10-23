#!/usr/bin/env python3
"""
GetTokenomics — Zero-Extension Token & AIU Telemetry Tracker for GitHub Copilot
https://github.com/ShahabName/GetTokenomics

Creates or updates daily GitHub Copilot Chat & Agent Mode telemetry in
`tokenomics-CCYYMMDD.csv` (29-column schema) by parsing local session logs from
`~/.copilot/session-state/<session-id>/events.jsonl`.

Features:
- 100% Python Standard Library (zero pip dependencies, no org permissions needed)
- Modular ON/OFF switch support via global.instructions.md (`TOKENOMICS_SWITCH: ON|OFF`),
  CLI flags (`--on` / `--off` / `--status`), or environment variable (`GETTOKENOMICS_ENABLED`)
- Automatic multi-turn reconciliation (refreshes previous turns whose final tool-call
  telemetry settled after the turn ended)
- Cross-platform support (Windows, macOS, Linux)
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HEADERS: list[str] = [
    "timestamp_utc",
    "session_id",
    "challenge_or_task",
    "turn_index",
    "sequence_id",
    "initiator",
    "router_model",
    "source_model",
    "model_display_name",
    "reasoning_effort",
    "api_calls_count",
    "user_prompt_multiplier",
    "total_request_multiplier_cost",
    "total_input_tokens",
    "uncached_input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
    "tool_schema_tokens",
    "cache_hit_ratio_pct",
    "total_nano_aiu",
    "total_aiu_credits",
    "duration_ms",
    "ttft_ms",
    "tools_invoked",
    "finish_reason",
    "ai_credits_status",
    "prompt_summary",
]

DEFAULT_INSTRUCTIONS_CANDIDATES: list[Path] = [
    Path.home() / ".copilot" / "instructions" / "global.instructions.md",
    Path.home() / ".copilot" / "instructions" / "tokenomics.instructions.md",
]

SWITCH_PATTERN = re.compile(
    r"(TOKENOMICS_SWITCH\s*:\s*)(ON|OFF|TRUE|FALSE|1|0)",
    re.IGNORECASE,
)


def resolve_instructions_file(custom_path: str | None = None) -> Path | None:
    """Return the first existing instructions file containing or supporting the switch."""
    if custom_path:
        p = Path(custom_path).expanduser()
        return p if p.exists() else None
    for candidate in DEFAULT_INSTRUCTIONS_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def is_tokenomics_enabled(custom_instructions_path: str | None = None) -> tuple[bool, str]:
    """
    Check whether GetTokenomics is enabled via:
    1. Environment variable GETTOKENOMICS_ENABLED
    2. TOKENOMICS_SWITCH: ON|OFF inside global.instructions.md / tokenomics.instructions.md
    Defaults to True (ON) if no explicit OFF switch is found.
    """
    env_val = os.environ.get("GETTOKENOMICS_ENABLED", "").strip().upper()
    if env_val in {"0", "OFF", "FALSE", "NO", "DISABLED"}:
        return False, "environment variable GETTOKENOMICS_ENABLED"
    if env_val in {"1", "ON", "TRUE", "YES", "ENABLED"}:
        return True, "environment variable GETTOKENOMICS_ENABLED"

    inst_file = resolve_instructions_file(custom_instructions_path)
    if inst_file and inst_file.exists():
        try:
            content = inst_file.read_text(encoding="utf-8", errors="ignore")
            match = SWITCH_PATTERN.search(content)
            if match:
                state = match.group(2).upper()
                enabled = state in {"ON", "TRUE", "1"}
                return enabled, f"{inst_file} (TOKENOMICS_SWITCH: {state})"
        except OSError:
            pass

    return True, "default (ON)"


def set_tokenomics_switch(enable: bool, custom_instructions_path: str | None = None) -> Path:
    """Toggle `TOKENOMICS_SWITCH: ON` or `TOKENOMICS_SWITCH: OFF` in the instructions file."""
    target = (
        Path(custom_instructions_path).expanduser()
        if custom_instructions_path
        else DEFAULT_INSTRUCTIONS_CANDIDATES[0]
    )
    new_state = "ON" if enable else "OFF"
    if target.exists():
        content = target.read_text(encoding="utf-8", errors="ignore")
        if SWITCH_PATTERN.search(content):
            updated = SWITCH_PATTERN.sub(rf"\g<1>{new_state}", content)
            target.write_text(updated, encoding="utf-8")
            return target
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(f"\n- **Tokenomics Tracking Switch**: `TOKENOMICS_SWITCH: {new_state}`\n")
    return target


def infer_challenge_or_task(summary: str) -> str:
    """Derive a concise, human-readable task or challenge slug from the user prompt."""
    s = summary.lower()

    # Detect explicit Challenge numbers (e.g., Challenge 7, C11)
    for idx in range(25, -1, -1):
        if re.search(rf"\b(challenge\s*{idx}|c{idx})\b", s):
            return f"C{idx}-Task"

    # Detect GitHub / ADO issue or PR references (e.g., #42, AB#35, PR #12)
    ab_match = re.search(r"\bab#(\d+)\b", s)
    if ab_match:
        return f"AB-{ab_match.group(1)}-Task"
    pr_match = re.search(r"\b(?:pr|pull\s+request|issue)\s*#?(\d+)\b", s)
    if pr_match:
        return f"Issue-PR-{pr_match.group(1)}"

    # Detect slash commands or skills (e.g., /code-review, /rpi-quick)
    skill_match = re.search(r"(?:^|\s)/([a-z0-9][a-z0-9_-]{1,30})\b", s)
    if skill_match:
        return f"Skill-{skill_match.group(1)}"

    words = re.findall(r"[A-Za-z0-9]+", summary)
    return "-".join(words[:4]) if words else "General-Prompt"


def clean_user_prompt(raw_content: str) -> str:
    """Strip IDE/system XML wrappers from user message content to extract clean prompt text."""
    xml_tags = [
        "current_datetime",
        "mode_changed_notice",
        "system_reminder",
        "ide_selection",
        "tagged_files",
        "context",
        "attachment",
    ]
    cleaned = raw_content
    for tag in xml_tags:
        cleaned = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", "", cleaned, flags=re.S | re.I)

    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return text[:240]


def parse_session_turns(session_id: str, events_path: str | Path) -> list[dict[str, str]]:
    """Parse all prompt turns and usage telemetry from a Copilot session events.jsonl file."""
    path_obj = Path(events_path)
    if not path_obj.exists():
        return []

    turns: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None
    pending_user_msg: str | None = None
    pending_user_ts: str | None = None

    with path_obj.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue

            ev_type = ev.get("type")
            ts = ev.get("timestamp", "")
            data = ev.get("data", {})

            if ev_type == "user.message":
                raw = data.get("content", "")
                is_auto_continue = (
                    "You have not yet marked the task as complete using the task_complete tool"
                    in raw
                )
                if not is_auto_continue:
                    cleaned = clean_user_prompt(raw)
                    if cleaned:
                        pending_user_msg = cleaned
                        pending_user_ts = ts

            elif ev_type == "session.usage_record":
                usage = data.get("usage", {})
                init = usage.get("initiator", "agent")

                if init == "user" or current_turn is None:
                    if current_turn is not None and current_turn["records"]:
                        turns.append(current_turn)
                    prompt_text = pending_user_msg or "(user prompt)"
                    prompt_ts = pending_user_ts or ts
                    pending_user_msg = None
                    pending_user_ts = None
                    current_turn = {
                        "timestamp_utc": prompt_ts,
                        "prompt_summary": prompt_text,
                        "records": [(ts, usage)],
                    }
                else:
                    current_turn["records"].append((ts, usage))

    if current_turn is not None and current_turn["records"]:
        turns.append(current_turn)

    rows: list[dict[str, str]] = []
    for idx, t in enumerate(turns, 1):
        recs = [u for _, u in t["records"]]
        first_u = recs[0]
        last_u = recs[-1]

        main_seqs = [
            u.get("accounting", {}).get("sequence")
            for u in recs
            if u.get("initiator") != "sub-agent"
            and u.get("accounting", {}).get("sequence") is not None
        ]
        sub_seqs = [
            u.get("accounting", {}).get("sequence")
            for u in recs
            if u.get("initiator") == "sub-agent"
            and u.get("accounting", {}).get("sequence") is not None
        ]
        if main_seqs:
            seq_str = f"{main_seqs[0]}-{main_seqs[-1]}" if len(main_seqs) > 1 else f"{main_seqs[0]}"
        else:
            seq_str = "1"
        if sub_seqs:
            seq_str += f"+sub({sub_seqs[0]}-{sub_seqs[-1]})"

        inits: list[str] = []
        for u in recs:
            ini = u.get("initiator", "agent")
            if ini not in inits:
                inits.append(ini)
        initiator_str = "+".join(inits)

        fusion = first_u.get("fusion") or last_u.get("fusion") or {}
        router_model = fusion.get("syntheticModel", "direct")
        source_model = first_u.get("model", "unknown")
        model_display = first_u.get("modelDisplayName", source_model)
        effort = first_u.get("reasoningEffort", "default")

        api_calls_count = len(recs)
        user_mult = sum(float(u.get("cost", 0.0)) for u in recs if u.get("initiator") == "user")
        if user_mult == 0.0:
            user_mult = float(first_u.get("cost", 1.0))
        total_cost = sum(float(u.get("cost", 0.0)) for u in recs)

        total_in = sum(int(u.get("inputTokens", 0)) for u in recs)
        uncached_in = 0
        for u in recs:
            td_list = u.get("copilotUsage", {}).get("tokenDetails", [])
            uncached_in += sum(
                int(td.get("tokenCount", 0)) for td in td_list if td.get("tokenType") == "input"
            )

        cache_r = sum(int(u.get("cacheReadTokens", 0)) for u in recs)
        cache_w = sum(int(u.get("cacheWriteTokens", 0)) for u in recs)
        out_tok = sum(int(u.get("outputTokens", 0)) for u in recs)
        reas_tok = sum(int(u.get("reasoningTokens", 0)) for u in recs)
        tool_tok = max((int(u.get("toolTokenCount", 0)) for u in recs), default=0)

        cache_hit_pct = round((cache_r / total_in) * 100.0, 2) if total_in > 0 else 0.0
        total_nano = sum(int(u.get("copilotUsage", {}).get("totalNanoAiu", 0)) for u in recs)
        total_aiu = round(total_nano / 1e9, 6)

        dur_ms = sum(int(u.get("duration", 0)) for u in recs)
        ttft_ms = round(float(first_u.get("timeToFirstTokenMs", 0.0)), 1)

        tool_agg: dict[str, int] = {}
        for u in recs:
            tc = u.get("toolCounts") or {}
            for k, v in tc.items():
                tool_agg[k] = tool_agg.get(k, 0) + int(v)
        tools_str = ";".join(f"{k}:{v}" for k, v in sorted(tool_agg.items())) if tool_agg else "none"

        finish_reason = last_u.get("finishReason", "stop")
        credits_status = last_u.get("aiCreditsStatus", "complete")
        summary = t["prompt_summary"]
        task_label = infer_challenge_or_task(summary)

        rows.append(
            {
                "timestamp_utc": t["timestamp_utc"],
                "session_id": session_id,
                "challenge_or_task": task_label,
                "turn_index": str(idx),
                "sequence_id": seq_str,
                "initiator": initiator_str,
                "router_model": router_model,
                "source_model": source_model,
                "model_display_name": model_display,
                "reasoning_effort": effort,
                "api_calls_count": str(api_calls_count),
                "user_prompt_multiplier": f"{user_mult:.2f}",
                "total_request_multiplier_cost": f"{total_cost:.2f}",
                "total_input_tokens": str(total_in),
                "uncached_input_tokens": str(uncached_in),
                "cache_read_tokens": str(cache_r),
                "cache_write_tokens": str(cache_w),
                "output_tokens": str(out_tok),
                "reasoning_tokens": str(reas_tok),
                "tool_schema_tokens": str(tool_tok),
                "cache_hit_ratio_pct": f"{cache_hit_pct:.2f}",
                "total_nano_aiu": str(total_nano),
                "total_aiu_credits": f"{total_aiu:.6f}",
                "duration_ms": str(dur_ms),
                "ttft_ms": f"{ttft_ms:.1f}",
                "tools_invoked": tools_str,
                "finish_reason": finish_reason,
                "ai_credits_status": credits_status,
                "prompt_summary": summary,
            }
        )
    return rows


def update_csv(
    csv_path: str | Path,
    session_ids: list[str],
    state_root: str | Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Upsert parsed session turns into the daily CSV file while preserving earlier sessions."""
    csv_file = Path(csv_path)
    state_dir = Path(state_root)
    existing_rows: list[dict[str, str]] = []

    if csv_file.exists():
        with csv_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r and r.get("session_id"):
                    existing_rows.append(r)

    index_map = {(r["session_id"], str(r["turn_index"])): i for i, r in enumerate(existing_rows)}
    latest_session_rows: list[dict[str, str]] = []

    for sid in session_ids:
        ev_path = state_dir / sid / "events.jsonl"
        parsed = parse_session_turns(sid, ev_path)
        for row in parsed:
            key = (row["session_id"], str(row["turn_index"]))
            if key in index_map:
                existing_rows[index_map[key]] = row
            else:
                index_map[key] = len(existing_rows)
                existing_rows.append(row)
        if parsed:
            latest_session_rows = parsed

    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with csv_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for r in existing_rows:
            writer.writerow({h: r.get(h, "") for h in HEADERS})

    return existing_rows, latest_session_rows


def format_markdown_summary(row: dict[str, str], csv_path: Path) -> str:
    """Format the latest turn row as a Markdown summary block ready for Copilot responses."""
    posix_path = csv_path.resolve().as_posix()
    csv_name = csv_path.name
    return "\n".join(
        [
            "## Tokenomics",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| **Model** | {row['model_display_name']} (`{row['source_model']}`, effort: `{row['reasoning_effort']}`) |",
            f"| **Turn / API Calls** | Turn `{row['turn_index']}` (`{row['api_calls_count']}` API calls, sequence `{row['sequence_id']}`) |",
            f"| **Input Tokens** | `{int(row['total_input_tokens']):,}` (Uncached: `{int(row['uncached_input_tokens']):,}`, Cache Read: `{int(row['cache_read_tokens']):,}`) |",
            f"| **Output / Reasoning Tokens** | Output: `{int(row['output_tokens']):,}` / Reasoning: `{int(row['reasoning_tokens']):,}` |",
            f"| **Cache Hit Ratio** | `{row['cache_hit_ratio_pct']}%` |",
            f"| **Total NanoAIU** | `{int(row['total_nano_aiu']):,}` |",
            f"| **Total AIU / AIC Credits** | `{row['total_aiu_credits']}` |",
            f"| **Duration / TTFT** | `{int(row['duration_ms']):,} ms` (TTFT: `{row['ttft_ms']} ms`) |",
            f"| **Daily CSV Log** | [{csv_name}]({posix_path}) |",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GetTokenomics: Create or update daily tokenomics-CCYYMMDD.csv telemetry."
    )
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace directory where tokenomics-CCYYMMDD.csv is stored (default: cwd)",
    )
    parser.add_argument(
        "--date",
        default=datetime.datetime.now().strftime("%Y%m%d"),
        help="Date suffix in CCYYMMDD format (default: today)",
    )
    parser.add_argument(
        "--session-id",
        action="append",
        dest="session_ids",
        help="Specific Copilot session ID(s) to sync (auto-discovers latest if omitted)",
    )
    parser.add_argument(
        "--state-root",
        default=str(Path.home() / ".copilot" / "session-state"),
        help="Path to ~/.copilot/session-state directory",
    )
    parser.add_argument(
        "--instructions-file",
        default=None,
        help="Optional path to global.instructions.md to check/toggle TOKENOMICS_SWITCH",
    )
    parser.add_argument(
        "--on",
        action="store_true",
        help="Set TOKENOMICS_SWITCH: ON in global.instructions.md and exit",
    )
    parser.add_argument(
        "--off",
        action="store_true",
        help="Set TOKENOMICS_SWITCH: OFF in global.instructions.md and exit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print current TOKENOMICS_SWITCH status (ON or OFF) and exit",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if TOKENOMICS_SWITCH is set to OFF",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print a ready-to-paste Markdown ## Tokenomics table for the latest turn",
    )
    args = parser.parse_args()

    if args.on or args.off:
        target = set_tokenomics_switch(enable=bool(args.on), custom_instructions_path=args.instructions_file)
        new_state = "ON" if args.on else "OFF"
        print(f"TOKENOMICS_SWITCH: {new_state} (updated in {target})")
        return 0

    enabled, source = is_tokenomics_enabled(args.instructions_file)
    if args.status:
        state_str = "ON" if enabled else "OFF"
        print(f"TOKENOMICS_SWITCH: {state_str} (source: {source})")
        return 0

    if not enabled and not args.force:
        print(f"TOKENOMICS_STATUS: OFF (skipped via {source})")
        return 0

    state_root = Path(args.state_root).expanduser()
    session_ids: list[str] = args.session_ids or []

    if not session_ids and state_root.exists():
        candidates: list[tuple[float, str]] = []
        for entry in state_root.iterdir():
            if entry.is_dir():
                ev = entry / "events.jsonl"
                if ev.exists():
                    candidates.append((ev.stat().st_mtime, entry.name))
        candidates.sort(reverse=True)
        if candidates:
            session_ids = [candidates[0][1]]

    csv_name = f"tokenomics-{args.date}.csv"
    csv_path = Path(args.workspace) / csv_name
    all_rows, latest_rows = update_csv(csv_path, session_ids, state_root)

    print(f"CSV_PATH: {csv_path.resolve()}")
    print(f"TOTAL_ROWS: {len(all_rows)}")
    if latest_rows:
        last = latest_rows[-1]
        print(
            f"LATEST_TURN: session={last['session_id']} turn={last['turn_index']} "
            f"task={last['challenge_or_task']} model={last['source_model']} "
            f"calls={last['api_calls_count']} in={last['total_input_tokens']} "
            f"out={last['output_tokens']} cacheHit={last['cache_hit_ratio_pct']}% "
            f"aiu={last['total_aiu_credits']} durMs={last['duration_ms']}"
        )
        if args.markdown:
            print()
            print(format_markdown_summary(last, csv_path))

    return 0


if __name__ == "__main__":
    sys.exit(main())
