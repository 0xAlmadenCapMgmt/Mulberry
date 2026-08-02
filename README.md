# Mulberry — Multi-Framework Stock Analysis

```
███╗   ███╗██╗   ██╗██╗     ██████╗ ███████╗██████╗ ██████╗ ██╗   ██╗
████╗ ████║██║   ██║██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝
██╔████╔██║██║   ██║██║     ██████╔╝█████╗  ██████╔╝██████╔╝ ╚████╔╝
██║╚██╔╝██║██║   ██║██║     ██╔══██╗██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝
██║ ╚═╝ ██║╚██████╔╝███████╗██████╔╝███████╗██║  ██║██║  ██║   ██║
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
```

**Mulberry** evaluates a company through **five complementary frameworks**, blends
them into a single composite score and recommendation, then contextualizes the
result with **SEC-filing history**, an optional **AI-written thesis**, and a
**universe screener** — all rendered as interactive HTML from the command line or
a local web UI. It began as a Ben Graham value tool (formerly *Charlotte*) and now
goes well beyond classic value.

**New here?** → **[GETTING_STARTED.md](GETTING_STARTED.md)** has copy-paste startup commands.

| Lens | Weight\* | What it measures |
|---|---|---|
| **Value** | 30% | Margin of safety from six intrinsic-value methods (Graham + DCF + DDM) |
| **Quality** | 25% | Margins, return on equity, free-cash-flow conversion and consistency |
| **Growth** | 20% | Revenue/EPS/FCF compounding, growth consistency, PEG (GARP) |
| **Momentum** | 15% | 50/200-day trend, RSI, 52-week range position, trailing returns |
| **Dividend** | 10% | Yield, payout sustainability, dividend growth, track record |

\* Default `balanced` weights. Choose a different `--profile` (`deep_value`, `garp`,
`income`, `quality_growth`) to re-weight. Dividend weight is redistributed for
non-payers, and a severely negative margin of safety caps the recommendation at
HOLD — quality alone never justifies buying at any price.

## What's in a report

- Composite recommendation + 5-lens radar and scorecard
- **Six valuation methods**: Graham Number `√(22.5 × EPS × BVPS)`, Net-Net (NCAV),
  Normalized Earnings, Growth-Adjusted Earnings, two-stage **DCF** (with a
  discount-rate/terminal-growth sensitivity grid), and a **Dividend Discount Model**
- Relative-valuation multiples (EV/EBITDA, EV/Sales, P/FCF) and a forward-looking
  analyst panel
- **Peer-relative percentiles** (`--peers`) and **composite score history** across runs
- **SEC Filings & Trends** — multi-year XBRL balance-sheet trends, a filing timeline,
  a conservative red-flag scan (going-concern, notable 8-K items), and MD&A /
  Risk-Factor excerpts
- **Investment Thesis (AI-generated)** — a narrative thesis, bull/bear case, and
  risks synthesized from the metrics and filing text (optional; see below)
- Financial-health scorecard, per-lens detail tables, and a data-confidence badge
- **Glossary & Formulas** — plain-language definitions and formulas for every
  term, with hover tooltips on metrics throughout the report (also browsable at
  `/glossary` in the web UI)
- **Ask the analysis** — a grounded, tool-using assistant (`ask` on the CLI, a
  `/ask` chat page on the web) that answers questions about a report by looking
  up its computed metrics, drilling into a lens, defining a term, or comparing
  another ticker (optional; needs an `ANTHROPIC_API_KEY`)

Filings, the AI thesis, and the assistant are **context only** — they never
change the numeric scores or the recommendation.

## Install

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

Core data (Yahoo Finance + SEC EDGAR) needs **no API keys**.

> **Running on a path with spaces** (like `Mulberry (Financial Analysis Tool)`):
> the generated `mulberry` / `fa` shortcut scripts break, so invoke as a module:
> `./venv/bin/python -m mulberry.cli <command>`. See
> [GETTING_STARTED.md](GETTING_STARTED.md).

## Usage

```bash
# Web UI — analyze, screen, ask, glossary, and report history at http://127.0.0.1:8000
mulberry serve

# Single-name report (open in browser)
mulberry analyze AAPL -b
mulberry analyze KO --peers PEP,KDP,MNST --profile income -b
mulberry analyze NVDA --no-filings -b        # skip the SEC fetch

# Rank a universe → HTML + CSV
mulberry screen AAPL MSFT KO PLTR -b
mulberry screen --universe watchlist.txt --profile deep_value -b

# Ask questions about an analysis (grounded, tool-using assistant; needs ANTHROPIC_API_KEY)
mulberry ask AAPL "why is the composite only 60?"
mulberry ask KO                              # interactive session

# Maintenance
mulberry info                                # config + paths
mulberry test-api                            # verify Yahoo Finance connectivity
mulberry clear-cache                         # drop cached ticker data
```

`fa` is a short alias for `mulberry` (both break on space-containing paths — use
the module form above there). Full flags: `mulberry <command> --help`.

## Configuration (optional)

Copy `config/.env.example` to `config/.env`, or export in your shell:

```bash
CACHE_TTL_FUNDAMENTALS=86400   # yfinance bundle cache TTL (seconds)
CACHE_TTL_FILINGS=604800       # SEC filings cache TTL (7 days)
AAA_BOND_YIELD=5.0             # AAA yield used in the growth-adjusted formula (%)
SEC_USER_AGENT="Your Name you@example.com"   # SEC etiquette for EDGAR requests
ANTHROPIC_API_KEY=sk-ant-...   # enables the AI thesis section (omitted without it)
THESIS_MODEL=claude-opus-4-8   # override the thesis model (optional)
```

## Project structure

```
mulberry/
├── api/               # data sources
│   ├── yahoo_finance.py   # market data + fundamentals
│   └── sec_edgar.py       # SEC EDGAR client (filings + XBRL)
├── core/
│   ├── graham.py · dcf.py · dividend.py     # valuation methods
│   ├── quality.py · growth.py · technicals.py  # lens engines
│   ├── relative.py · multiples.py · forward.py # peers, multiples, estimates
│   ├── filings.py         # SEC filing timeline, trends, red flags, excerpts
│   ├── data_quality.py    # per-lens data-confidence scoring
│   ├── composite.py       # weighted multi-framework blend + profiles
│   └── stock_analysis.py  # data fetch + pipeline orchestration
├── ai/thesis.py       # AI investment-thesis synthesis (Anthropic)
├── cache/             # pickle raw-data cache + score history
├── reports/           # HTML report + universe-screen generators
├── visualization/     # Plotly chart builders
├── templates/         # report Jinja2 templates
├── web/               # FastAPI front end (app + page templates)
└── cli.py             # Click CLI
```

## Technology

Python 3.9+ · Click + Rich · FastAPI + Uvicorn (web) · yfinance · pandas · Plotly ·
Jinja2 · requests (SEC EDGAR) · anthropic (optional AI thesis). Fully tested
across Python 3.9–3.11 in CI.

## Disclaimer

This tool is for educational and informational purposes only. It does not
constitute financial, investment, or trading advice. Always conduct your own due
diligence and consult a qualified financial advisor before making investment
decisions. Past performance does not guarantee future results.

## References

- Graham, Benjamin. *The Intelligent Investor*. Harper Business, 1949.
- Graham, Benjamin & Dodd, David. *Security Analysis*. McGraw-Hill, 1934.
- Lynch, Peter. *One Up on Wall Street*. Simon & Schuster, 1989.
- Damodaran, Aswath. *Investment Valuation*. Wiley, 2012.
