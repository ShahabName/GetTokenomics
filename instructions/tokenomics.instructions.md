---
description: "GetTokenomics — Automatic per-prompt token, cache hit, and AIU/AIC credit telemetry tracker for GitHub Copilot."
applyTo: "**"
---

# GetTokenomics — Modular Instructions

## Record and report daily tokenomics at the end of execution

- **Tokenomics Tracking Switch**: `TOKENOMICS_SWITCH: OFF` *(Default: `OFF` for zero token usage in chat — run `python "C:\Users\YourAliasName\.copilot\instructions\update-tokenomics.py"` in your terminal at the end of the day to update `tokenomics-CCYYMMDD.csv` with 0 tokens consumed. Change to `ON` or run `--on` if you want a live `## Tokenomics` preview table in GHCP Chat at the end of each prompt, which consumes a small fraction of tokens)*
- **Switch Rule**: Before recording or reporting tokenomics, check `TOKENOMICS_SWITCH` above. If it is set to `OFF`, skip running `update-tokenomics.py`, do not create or modify `tokenomics-CCYYMMDD.csv` during the chat turn, and omit the `## Tokenomics` section from the response.

When `TOKENOMICS_SWITCH: ON`, at the end of every prompt or task execution, record the prompt's tokenomics and AIC/AIU consumption in today's daily CSV file in the workspace root (`tokenomics-CCYYMMDD.csv`, where `CCYYMMDD` is the current date in `YYYYMMDD` format, such as `tokenomics-20261024.csv`) and display a summary in the final response.

- Check whether `tokenomics-CCYYMMDD.csv` exists in the current workspace root directory with the following 29 header columns:
  ```csv
  timestamp_utc,session_id,challenge_or_task,turn_index,sequence_id,initiator,router_model,source_model,model_display_name,reasoning_effort,api_calls_count,user_prompt_multiplier,total_request_multiplier_cost,total_input_tokens,uncached_input_tokens,cache_read_tokens,cache_write_tokens,output_tokens,reasoning_tokens,tool_schema_tokens,cache_hit_ratio_pct,total_nano_aiu,total_aiu_credits,duration_ms,ttft_ms,tools_invoked,finish_reason,ai_credits_status,prompt_summary
  ```
- If `tokenomics-CCYYMMDD.csv` does not exist yet, create it with the 29 header columns above.
- If `tokenomics-CCYYMMDD.csv` already exists, append the latest prompt turn tokenomics data from `C:\Users\YourAliasName\.copilot\session-state\<session-id>\events.jsonl` (or `~/.copilot/session-state/<session-id>/events.jsonl` on macOS/Linux) and refresh any previous turn in the session whose final tool-call usage settled after the prior turn. Run:
  ```bash
  python "C:\Users\YourAliasName\.copilot\instructions\update-tokenomics.py"
  ```
  *(or on macOS/Linux: `python3 "$HOME/.copilot/instructions/update-tokenomics.py"`)* to perform this check, creation, and append automatically.
- At the end of every prompt response (immediately above `## Files`), include a `## Tokenomics` section showing the tokenomics usage data recorded in `tokenomics-CCYYMMDD.csv` (model, API calls, input/cache/output/reasoning tokens, cache hit %, total NanoAIU, total AIU/AIC credits, duration, and a clickable link to `[tokenomics-CCYYMMDD.csv](C:/full/absolute/path/to/tokenomics-CCYYMMDD.csv)` using its absolute filesystem path with `/` separators).

## Report generated files at the end of execution

At the end of every prompt or task execution, list every file that was created, modified, or deleted during that run.

- Place the list at the very end of the final response, under a `## Files` heading.
- Group by action: `Created`, `Modified`, `Deleted`.
- For **Created** and **Modified** files, every entry **must be a clickable Markdown link** that opens the file in VS Code when clicked:
  - Use the workspace-relative path (or file name if outside the workspace) as the link text, and the **full absolute filesystem path with forward slashes (`/`)** as the link target: `[relative/path/to/file.ext](C:/full/absolute/path/to/file.ext)`.
  - Never use relative paths as the link target `(src/index.ts)` or `file://` URIs, as VS Code Chat requires the absolute filesystem path with `/` separators to make links clickable.
  - If the path contains spaces, wrap the target in angle brackets: `[path/with spaces/file.ext](<C:/full/absolute/path/with spaces/file.ext>)`.
- For **Deleted** files (which no longer exist on disk and cannot be opened), render the workspace-relative path as plain inline code without a link: `` - `src/legacy/old-format.ts` ``.
- Include generated artifacts as well as source edits: build output, exported media, logs, scratch/temp files, and files written by scripts or terminal commands.
- If a run produced no file changes, state `No files were created or modified.`

## Preserve default VS Code chat output

- Recording tokenomics (`update-tokenomics.py`) and appending `## Tokenomics` and `## Files` are strictly additive and must **never** replace, suppress, or alter VS Code's normal chat response or built-in tool defaults.
- Always display the complete user-facing explanation, analysis, or report in the chat response, with `## Tokenomics` and `## Files` appended at the end.
