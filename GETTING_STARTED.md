# Getting Started with Mulberry

Mulberry is a multi-framework stock-analysis tool. It blends value, quality,
growth, dividend, and momentum lenses into a composite score, layers on SEC
filing context and an optional AI thesis, and renders it all as an interactive
HTML report — from the command line or a local web UI.

- **Requirements:** Python 3.9+ (3.9, 3.10, and 3.11 are tested in CI).
- **No API keys required** for the core tool — market data comes from Yahoo
  Finance and filings from SEC EDGAR (both free). Two optional keys unlock extra
  sections (see [Optional keys](#optional-keys)).

---

## 1. Install (one time)

From the project root:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -e .
```

That installs Mulberry and all dependencies into a local `venv/`.

> ### ⚠️ Important: how to run Mulberry on this machine
> This project folder — `Mulberry (Financial Analysis Tool)` — has **spaces and
> parentheses in its path**, which breaks the generated `mulberry` / `fa`
> shortcut scripts. On this machine, always invoke Mulberry as a module:
>
> ```bash
> ./venv/bin/python -m mulberry.cli <command>
> ```
>
> Every command below uses that form. (If you ever move the project to a
> space-free path, the shorter `mulberry <command>` / `fa <command>` aliases
> work too.)

---

## 2. Launch the web UI  ← the easy way

```bash
./venv/bin/python -m mulberry.cli serve
```

Then open **http://127.0.0.1:8000** in your browser. Press `Ctrl+C` to stop.

The web app has three pages:

| Page | URL | What it does |
|------|-----|--------------|
| **Analyze** | `/` | Ticker box + controls (profile, peers, filings, thesis) → full report |
| **Screen** | `/screen` | Rank a list of tickers by composite score (HTML + CSV) |
| **History** | `/reports` | Browse every report you've generated |

**Options:**

```bash
./venv/bin/python -m mulberry.cli serve --port 9000     # if 8000 is busy
./venv/bin/python -m mulberry.cli serve --host 0.0.0.0  # reachable on your LAN
./venv/bin/python -m mulberry.cli serve --reload        # auto-restart on edits (dev)
```

---

## 3. Or use the command line

Generate a single-name report and open it in your browser:

```bash
./venv/bin/python -m mulberry.cli analyze AAPL -b
```

More examples:

```bash
# Peer-relative comparison + income-focused weighting
./venv/bin/python -m mulberry.cli analyze KO --peers PEP,KDP,MNST --profile income -b

# Skip the slower SEC-filings fetch
./venv/bin/python -m mulberry.cli analyze NVDA --no-filings -b

# Screen a universe → ranked HTML + a CSV alongside it
./venv/bin/python -m mulberry.cli screen AAPL MSFT KO PLTR -b

# Screen from a file (one ticker per line)
./venv/bin/python -m mulberry.cli screen --universe watchlist.txt --profile deep_value -b
```

Reports are written to `output/reports/` and cached data to `.cache/` (both
git-ignored).

---

## Common flags

| Flag | Applies to | Default | Meaning |
|------|-----------|---------|---------|
| `-b`, `--open-browser` | analyze, screen | off | Open the report when done |
| `-o PATH`, `--output` | analyze, screen | auto | Custom output path |
| `--profile NAME` | analyze, screen | `balanced` | Weighting: `balanced`, `deep_value`, `garp`, `income`, `quality_growth` |
| `--peers T1,T2` | analyze | none | Peer tickers for relative percentiles |
| `--filings / --no-filings` | analyze | **on** | SEC EDGAR trends, red flags, MD&A excerpts |
| `--thesis / --no-thesis` | analyze | **on*** | AI narrative (\*needs a key — see below) |

Full command list: `./venv/bin/python -m mulberry.cli --help`

---

## Optional keys

Both are optional. Set them **in the same shell before running** (or add them to
`config/.env` — copy `config/.env.example` to start). Without them, the tool runs
fine and simply omits the corresponding extras.

```bash
# AI investment thesis (Phase 4). Without this, the "Investment Thesis"
# report section is silently skipped.
export ANTHROPIC_API_KEY=sk-ant-...

# SEC EDGAR etiquette (Phase 3). Filings work without it, but SEC asks for a
# real contact string in the request User-Agent.
export SEC_USER_AGENT="Your Name your.email@example.com"

./venv/bin/python -m mulberry.cli serve      # keys picked up from the environment
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `command not found: fa` or a shebang error | Use the module form: `./venv/bin/python -m mulberry.cli …` (the space in the folder path breaks the shortcut scripts). |
| `Address already in use` on serve | A server is already running — use `--port 9000`, or stop the existing one. |
| No "Investment Thesis" section in the report | `ANTHROPIC_API_KEY` isn't set in the serving shell. Export it, then restart `serve`. |
| Analysis fails for a ticker | Confirm it's a valid US ticker with a live network. `clear-cache` forces a fresh fetch. |
| Web deps missing | `pip install -e .` (or `pip install fastapi uvicorn python-multipart`). |

---

## Useful maintenance commands

```bash
./venv/bin/python -m mulberry.cli info          # show config + paths
./venv/bin/python -m mulberry.cli test-api      # verify Yahoo Finance connectivity
./venv/bin/python -m mulberry.cli clear-cache   # drop cached ticker data
./venv/bin/python -m pytest -q                  # run the test suite
```
