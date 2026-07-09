# Loblaws

## Cursor Cloud specific instructions

This repository is **not a software application** — it holds business/consulting deliverables
(strategy decks, data analyses, written assessments), not a runnable service.

- The `main` branch contains only this `README.md`/`AGENTS.md`. There is nothing to serve,
  build, migrate, or connect to on `main` — no package manifests, no databases, no web app.
- The actual deliverables live on the `cursor/*` feature branches, e.g.:
  - `cursor/loblaw-discount-case-deck-926f` — discount-division strategy case: an XLSX source
    workbook plus a Python generator (`scripts/build_loblaw_case_outputs.py`) that emits a PDF
    deck, CSV/SQL/Markdown/HTML appendices into `output/`.
  - `cursor/psm-mls-feed-analysis-b935` — MLS feed operations analysis (charts, CSV, PPTX, md).
  - `cursor/vp-ready-cs-assessment-61f0` — customer-success written assessment (md/html/pdf).

### Runtime / dependencies
- Only **Python 3** (stdlib) is required. No `pip install` step exists — the deck generator
  deliberately uses only the standard library so it runs in a minimal environment.

### Running the only executable (deck generator)
Because it lives on another branch, run it without leaving `main` by using a git worktree:

```bash
git worktree add /tmp/deck-wt origin/cursor/loblaw-discount-case-deck-926f
cd /tmp/deck-wt && python3 scripts/build_loblaw_case_outputs.py   # writes to output/
# cleanup: cd /workspace && git worktree remove /tmp/deck-wt --force
```

- The script reads `source_data/super_market_strategy_analytics_case.xlsx` if present; otherwise
  it downloads the workbook from a Google Sheets export URL (needs network access).
- Output is reproducible: regenerating matches the committed files in `output/` (empty `git diff`).

### Lint / test / build
There is no lint config, no test suite, and no build system in this repo. "Build" == running the
generator script above.
