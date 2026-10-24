# How I Accidentally Built a Zero-Extension Tokenomics & AIU Tracker for GitHub Copilot (And How You Can Set It Up in 2 Minutes)

**By Mohammed Shahab (@ShahabName)**  
*LinkedIn:* [https://www.linkedin.com/in/shahabm/](https://www.linkedin.com/in/shahabm/)  
*Open-Source Repository:* [https://github.com/ShahabName/GetTokenomics](https://github.com/ShahabName/GetTokenomics)  
*Interactive Setup Website:* [https://shahabname.github.io/GetTokenomics/](https://shahabname.github.io/GetTokenomics/)

![GetTokenomics Animated Demo](../docs/assets/gettokenomics-demo.gif)

---

## The Accidental Discovery

When you work with **Agentic AI** in **GitHub Copilot Chat (Agent Mode)** all day—running multi-step coding tasks, invoking MCP servers, delegating to sub-agents, and iterating across large codebases—one question inevitably comes up:

> *"How many tokens, cached reads, API calls, and AIU/AIC credits did that prompt actually consume—and which underlying model served it?"*

Normally, getting that level of telemetry in an enterprise environment feels impossible without:
1. Installing a third-party VS Code extension (which many enterprise security policies block),
2. Requesting organization-level admin permissions or billing API keys, or
3. Setting up a proxy server between your IDE and the LLM endpoint.

While inspecting how Copilot Agent Mode maintains state across multi-turn sessions on my machine, I stumbled upon something remarkable: **GitHub Copilot already writes a rich, structured JSONL event stream locally inside your user profile directory** (`~/.copilot/session-state/<session-id>/events.jsonl`).

Even better? By combining **one zero-dependency Python script** (`update-tokenomics.py`) with **GitHub Copilot's personal `global.instructions.md`** file, you can instruct Copilot to automatically parse that local event stream at the end of every prompt, log **29 granular telemetry columns** into a daily CSV (`tokenomics-CCYYMMDD.csv`), and print a live **`## Tokenomics` scorecard** right inside your chat response!

* **No VS Code extension required.**
* **No `pip install` packages required** (100% Python 3 Standard Library).
* **No organization admin approval or API keys required.**
* **Includes a 1-line `TOKENOMICS_SWITCH: ON | OFF` toggle** so you can turn it on or off anytime.

It was a complete accidental discovery—and it turned out to be so genuinely useful that I packaged it under the **MIT License** as [**GetTokenomics**](https://github.com/ShahabName/GetTokenomics) so everyone in the community can use it.

---

## What GetTokenomics Captures on Every Prompt (29 Columns)

Every time a prompt finishes in GitHub Copilot, `update-tokenomics.py` aggregates all API calls (including tool calls and sub-agent sequences) for that turn and records:

1. **Model & Routing Intelligence**: `router_model`, `source_model` (e.g., `claude-sonnet-4.5`, `gpt-5.3-codex`, `gemini-4-argon`), `model_display_name`, `reasoning_effort`, `initiator` (`user+agent+sub-agent`), and `api_calls_count`.
2. **Deep Token Economics**: `total_input_tokens`, `uncached_input_tokens`, `cache_read_tokens`, `cache_write_tokens`, `output_tokens`, `reasoning_tokens`, `tool_schema_tokens`, and `cache_hit_ratio_pct` (often `94%–99%` on multi-step agent runs!).
3. **Billing Multipliers & AIU/AIC Credits**: `user_prompt_multiplier`, `total_request_multiplier_cost`, `total_nano_aiu`, and `total_aiu_credits`.
4. **Latency & Tool Telemetry**: `duration_ms`, `ttft_ms` (Time-To-First-Token), `tools_invoked` (exact histogram like `edit:3;powershell:2;view:9`), `finish_reason`, and a clean `prompt_summary`.

### Multi-Turn Settlement Reconciliation
In Agentic workflows, the very last tool call of Turn $N$ (`task_complete` or final response) sometimes settles in `events.jsonl` a few milliseconds after the script runs. **GetTokenomics** automatically reconciles and refreshes any earlier turns in the same session on the next run—so your daily CSV is always 100% accurate.

---

## How to Set Up GetTokenomics in 2 Minutes

### Step 1: Download `update-tokenomics.py` into `~/.copilot/instructions/`

Open **PowerShell** (Windows) or **Terminal** (macOS/Linux) and download `update-tokenomics.py` into your `.copilot/instructions` directory:

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force "$HOME\.copilot\instructions" | Out-Null
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ShahabName/GetTokenomics/main/update-tokenomics.py" `
  -OutFile "$HOME\.copilot\instructions\update-tokenomics.py"
```

**macOS / Linux:**
```bash
mkdir -p "$HOME/.copilot/instructions"
curl -fsSL https://raw.githubusercontent.com/ShahabName/GetTokenomics/main/update-tokenomics.py \
  -o "$HOME/.copilot/instructions/update-tokenomics.py"
```

![Step 1: Download update-tokenomics.py](../docs/assets/screenshots/step-1-download-script.png)

---

### Step 2: Add the Modular Snippet (with the `ON/OFF` Switch) to `global.instructions.md`

Open your personal global instructions file at `C:\Users\YourAliasName\.copilot\instructions\global.instructions.md` (or `~/.copilot/instructions/global.instructions.md`) and add the block below:

````markdown
## Record and report daily tokenomics at the end of execution

- **Tokenomics Tracking Switch**: `TOKENOMICS_SWITCH: ON` *(Change to `OFF` to disable tokenomics CSV logging and response reporting; change to `ON` to enable)*
- **Switch Rule**: Before recording or reporting tokenomics, check `TOKENOMICS_SWITCH` above. If it is set to `OFF`, skip running `update-tokenomics.py`, do not create or modify `tokenomics-CCYYMMDD.csv`, and omit the `## Tokenomics` section from the response.

When `TOKENOMICS_SWITCH: ON`, at the end of every prompt or task execution, record the prompt's tokenomics and AIC/AIU consumption in today's daily CSV file in the workspace root (`tokenomics-CCYYMMDD.csv`, where `CCYYMMDD` is the current date in `YYYYMMDD` format, such as `tokenomics-20261024.csv`) and display a summary in the final response.

- Check whether `tokenomics-CCYYMMDD.csv` exists in the current workspace root directory with the following 29 header columns:
  ```csv
  timestamp_utc,session_id,challenge_or_task,turn_index,sequence_id,initiator,router_model,source_model,model_display_name,reasoning_effort,api_calls_count,user_prompt_multiplier,total_request_multiplier_cost,total_input_tokens,uncached_input_tokens,cache_read_tokens,cache_write_tokens,output_tokens,reasoning_tokens,tool_schema_tokens,cache_hit_ratio_pct,total_nano_aiu,total_aiu_credits,duration_ms,ttft_ms,tools_invoked,finish_reason,ai_credits_status,prompt_summary
  ```
- If `tokenomics-CCYYMMDD.csv` does not exist yet, create it with the 29 header columns above.
- If `tokenomics-CCYYMMDD.csv` already exists, append the latest prompt turn tokenomics data from `C:\Users\YourAliasName\.copilot\session-state\<session-id>\events.jsonl` (and refresh any previous turn in the session whose final tool-call usage settled after the prior turn). You can run `python "C:\Users\YourAliasName\.copilot\instructions\update-tokenomics.py"` to perform this check, creation, and append automatically.
- At the end of every prompt response (immediately above `## Files`), include a `## Tokenomics` section showing the tokenomics usage data recorded in `tokenomics-CCYYMMDD.csv` (model, API calls, input/cache/output/reasoning tokens, cache hit %, total NanoAIU, total AIU/AIC credits, duration, and a clickable link to `[tokenomics-CCYYMMDD.csv](C:/full/absolute/path/to/tokenomics-CCYYMMDD.csv)` using its absolute filesystem path with `/` separators).

## Preserve default VS Code chat output

- Recording tokenomics (`update-tokenomics.py`) and appending `## Tokenomics` and `## Files` are strictly additive and must **never** replace, suppress, or alter VS Code's normal chat response or built-in tool defaults.
- Always display the complete user-facing explanation, analysis, or report in the chat response, with `## Tokenomics` and `## Files` appended at the end.
````

![Step 2: Global Instructions with ON/OFF Switch](../docs/assets/screenshots/step-2-global-instructions-switch.png)

---

### Step 3: Watch Live Tokenomics Appear at the End of Every Prompt

Run any prompt in GitHub Copilot Chat. At the end of the response, Copilot automatically runs `update-tokenomics.py`, updates `tokenomics-CCYYMMDD.csv`, and displays your `## Tokenomics` table with a clickable link straight to the CSV file:

![Step 3: Live Copilot Chat Output](../docs/assets/screenshots/step-3-chat-tokenomics-output.png)

---

### Step 4: Flip the Switch `ON` or `OFF` Anytime

Need clean, minimal responses during a live presentation? Flip `TOKENOMICS_SWITCH: OFF` in `global.instructions.md`—or toggle it from your terminal in one second:

```bash
python "$HOME/.copilot/instructions/update-tokenomics.py" --off
python "$HOME/.copilot/instructions/update-tokenomics.py" --on
python "$HOME/.copilot/instructions/update-tokenomics.py" --status
```

![Step 4: 29-Column CSV & CLI Toggle](../docs/assets/screenshots/step-4-daily-csv-analytics.png)

---

## Try It Today & Share Your Feedback!

* 📦 **GitHub Repository (MIT License):** [https://github.com/ShahabName/GetTokenomics](https://github.com/ShahabName/GetTokenomics)
* 🌐 **Interactive Setup Website & Schema Explorer:** [https://shahabname.github.io/GetTokenomics/](https://shahabname.github.io/GetTokenomics/)
* 💼 **Connect on LinkedIn:** [https://www.linkedin.com/in/shahabm/](https://www.linkedin.com/in/shahabm/)

If you're benchmarking different models, optimizing prompt cache hit rates, or teaching Agentic AI workshops, give **GetTokenomics** a try and let me know what insights you uncover in your daily CSVs!

#AgenticAI #Tokenomics #TokenTracking #GitHubCopilot #AIEngineering #FinOps #DeveloperProductivity #LLMObservability #VSCode #OpenSource
