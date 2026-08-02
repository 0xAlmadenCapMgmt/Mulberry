# CLAUDE.md — Mulberry

Guidance for Claude Code sessions in this repo. Read `README.md`, `GETTING_STARTED.md`,
and `ROADMAP.md` for full context.

## What Mulberry is

A multi-framework stock-analysis tool (owner: Almaden Capital Management; began as
"Charlotte", a Graham value tool). It blends **five lenses** — value, quality,
growth, dividend, momentum — into a composite score, adds **SEC-filing context**
and an optional **AI thesis**, offers **universe screening**, and renders
interactive HTML from a CLI or a local FastAPI web UI. Guiding principle:
**contextualize analyses across past/present/future**, not point-in-time snapshots.

## Status

**v0.9.0 — all six roadmap phases complete and merged to `main`** (CI green on
Python 3.9–3.11). Repo is clean: only `main`. See `ROADMAP.md` for the phase log.

## Running it (IMPORTANT: path has spaces)

The project path `Mulberry (Financial Analysis Tool)` contains spaces/parens, which
**breaks the generated `mulberry` / `fa` entry-point scripts**. Always invoke as a
module:

```bash
./venv/bin/python -m mulberry.cli <command>   # analyze | screen | serve | info | test-api | clear-cache
./venv/bin/python -m pytest -q                # test suite: fully offline, ~175 tests
```

- Web UI: `serve` → http://127.0.0.1:8000 (pages: `/` analyze, `/screen`, `/reports`).
- Reports write to `output/reports/*.html` (+ `.csv` for screens); cache in `.cache/` (both git-ignored).
- Optional keys: `ANTHROPIC_API_KEY` (enables the AI thesis section), `SEC_USER_AGENT` (EDGAR etiquette). Both degrade gracefully when unset.

## Conventions / how we work here

- **Testing philosophy:** exact golden-value tests on deterministic formula helpers;
  behavioral tests on scoring aggregations. Everything offline — a patched-yfinance
  fixture (`tests/conftest.py`) and fake EDGAR/Anthropic clients; no network in tests.
  Keep the suite green.
- **Graceful degradation everywhere:** filings, thesis, and peer fetches must never
  break the core report if a data source is unavailable.
- **Filings & AI thesis are context only** — they never change the numeric scores or
  the recommendation.
- **Git flow:** feature branch per unit of work; detailed commit messages ending with
  the `Co-Authored-By: Claude Opus 4.8` trailer; PR bodies end with the Claude Code
  footer. Don't commit to `main` without reason; confirm before outward/irreversible
  actions (pushing to `main`, merging, deleting remote branches).
- **GitHub token scopes:** the keychain token has Contents:write + `workflow`, but
  **not** Pull-requests:write or Administration. So: pushing branches/workflow files
  works; opening/closing/merging PRs and renaming repos must be done by the user in
  the GitHub UI. (Deleting a PR's head branch auto-closes the PR — a useful workaround.)

## Architecture (where things live)

- `mulberry/api/` — `yahoo_finance.py` (market data), `sec_edgar.py` (filings/XBRL)
- `mulberry/core/` — lens engines (`graham`, `dcf`, `quality`, `growth`, `technicals`,
  `dividend`), `relative`/`multiples`/`forward` (peers/multiples/estimates),
  `filings.py`, `data_quality.py`, `composite.py` (weighting + profiles),
  `stock_analysis.py` (pipeline)
- `mulberry/ai/thesis.py` — Anthropic thesis synthesis (default model `claude-opus-4-8`)
- `mulberry/reports/` — `generator.py` (single-name), `screen.py` (universe)
- `mulberry/cache/` — `raw_cache.py` (pickle), `history.py` (score-over-time)
- `mulberry/web/app.py` — FastAPI front end (use the modern `TemplateResponse(request=…, name=…, context=…)` signature — the old positional order breaks on newer Starlette)
- `mulberry/visualization/charts.py`, `mulberry/templates/`, `mulberry/cli.py`
