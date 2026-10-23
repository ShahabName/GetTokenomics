# Changelog

All notable changes to **GetTokenomics** will be documented in this file.

## [1.0.0] - 2026-10-24

### Added
- **`update-tokenomics.py`**: Zero-dependency Python 3 script that parses `~/.copilot/session-state/<session-id>/events.jsonl` and writes/updates daily `tokenomics-CCYYMMDD.csv` files with a 29-column telemetry schema.
- **Modular ON/OFF Switch (`TOKENOMICS_SWITCH: ON | OFF`)**:
  - Toggle directly inside `~/.copilot/instructions/global.instructions.md` (or `tokenomics.instructions.md`).
  - Toggle from the terminal with `python update-tokenomics.py --on`, `--off`, and `--status`.
  - Override per shell session via `GETTOKENOMICS_ENABLED=0|1`.
- **Multi-Turn Telemetry Reconciliation**: Automatically refreshes previous turns in the same session whose final tool-call usage settled after the previous response completed.
- **Clickable File & CSV Links**: Modular instructions snippet ensuring `tokenomics-CCYYMMDD.csv` and all Created/Modified files in `## Files` render as clickable full-path links in VS Code Chat.
- **Interactive GitHub Pages Static Website (`docs/index.html`)**: Step-by-step visual setup guide with screenshots, interactive 29-column schema explorer, and live ON/OFF switch preview.
- **LinkedIn Article & Post Package (`linkedin/`)**: Ready-to-publish LinkedIn article, social post with hashtags, and animated SVG/GIF visual assets.
