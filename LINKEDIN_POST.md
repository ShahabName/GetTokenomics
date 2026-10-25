# LinkedIn Post — GetTokenomics Launch

> **Attachment to upload with this post:** `linkedin/gettokenomics-demo.gif` (or `docs/assets/screenshots/step-3-chat-tokenomics-output.png`)

---

🚀 **I accidentally built a zero-extension Tokenomics & AIU Credit Tracker for GitHub Copilot—and I’m open-sourcing it today!**

When running multi-step tasks in **GitHub Copilot (Agent Mode)**, I wanted to know what *actually* happened under the hood of each prompt:
• Which router & source LLM served the turn?
• How many API calls and sub-agent turns did a single prompt take?
• What was my prompt cache hit ratio (`94%–99%`) vs. uncached input tokens?
• How many **NanoAIU / AIU (AIC) credits** and reasoning tokens were consumed?

Most teams assume you need a custom VS Code extension, an enterprise API key, or org admin approval to track this.

Turns out—you don't need any of that! 💡

By using **1 pure-Python script** (`update-tokenomics.py`, zero `pip` packages) to parse your local Copilot session stream (`events.jsonl`), you get two flexible ways to track your tokenomics:

✅ **Zero Token Usage Mode (Default — `TOKENOMICS_SWITCH: OFF`):** Run `python ~/.copilot/instructions/update-tokenomics.py` from your terminal at the end of the day to log **29 telemetry columns** into `tokenomics-CCYYMMDD.csv` with **0 LLM tokens consumed**!
✅ **Optional Live In-Chat Preview (`--on`):** Want a live **`## Tokenomics` summary table** + clickable CSV/file links at the end of every GHCP Chat response? Run `--on` (or set `TOKENOMICS_SWITCH: ON`) anytime—uses only a tiny fraction of prompt-cached tokens!
✅ Auto-reconciles previous turns across all daily sessions when background tool calls settle
✅ **Zero extensions. Zero restrictions. Zero org permissions needed.**

🔗 **GitHub Repo (MIT License):** https://github.com/ShahabName/GetTokenomics
🌐 **Interactive Setup Guide & 29-Col Schema Explorer:** https://shahabname.github.io/GetTokenomics/
💼 **Connect with me on LinkedIn:** https://www.linkedin.com/in/shahabm/

Try the 2-minute setup and let me know what your prompt cache hit % looks like! 👇

#AgenticAI #Tokenomics #TokenTracking #GitHubCopilot #AIEngineering #LLMObservability #FinOps #DeveloperProductivity #VSCode #OpenSource #PromptEngineering
