# Contributing to GetTokenomics

Thank you for your interest in contributing to **GetTokenomics**! This project was born out of a simple, accidental discovery that turned into one of the most practical, zero-friction ways to track Agentic AI token consumption, cache efficiency, and AIU/AIC credits in GitHub Copilot.

## Core Design Principles

When proposing changes, please keep our core philosophy in mind:

1. **Zero Dependencies**: `update-tokenomics.py` must run using **only the Python 3 Standard Library** (`csv`, `json`, `pathlib`, `argparse`, `re`, `datetime`). Never require `pip install` or third-party packages.
2. **Zero Organization / Admin Permissions**: Everything must operate strictly on local user-directory files (`~/.copilot/session-state/` and `~/.copilot/instructions/`) without requiring VS Code extensions, API tokens, or enterprise admin consent.
3. **Instant ON/OFF Modularity**: The `TOKENOMICS_SWITCH: ON | OFF` toggle must always remain simple to flip either in the instructions file or via CLI (`--on` / `--off`).
4. **Backward-Compatible 29-Column Schema**: Preserve the canonical 29-column CSV header order so existing dashboards, Excel workbooks, and Power BI / Python analytics pipelines continue working without breakage.

## How to Contribute

### 1. Fork & Clone

```bash
git clone https://github.com/ShahabName/GetTokenomics.git
cd GetTokenomics
```

### 2. Run the Automated Tests

We use Python's built-in `unittest` framework (zero external test runners required):

```bash
python -m unittest discover -s tests -v
```

### 3. Test the CLI Locally

```bash
# Check switch status (defaults to OFF for zero chat token overhead)
python update-tokenomics.py --status

# Sync daily CSV from terminal with zero token consumption
python update-tokenomics.py

# Enable or disable live in-chat ## Tokenomics preview in global.instructions.md
python update-tokenomics.py --on
python update-tokenomics.py --off
```

### 4. Submit a Pull Request

1. Create a feature branch (`git checkout -b feat/your-feature-name`).
2. Ensure all unit tests pass (`python -m unittest discover -s tests -v`).
3. Update documentation (`README.md` and `docs/index.html` if UI/setup steps change).
4. Open a Pull Request with a clear description of the improvement.

## License

By contributing to GetTokenomics, you agree that your contributions will be licensed under the [MIT License](LICENSE).
