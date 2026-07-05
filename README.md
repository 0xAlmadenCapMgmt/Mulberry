# Mulberry — Multi-Framework Stock Analysis

```
███╗   ███╗██╗   ██╗██╗     ██████╗ ███████╗██████╗ ██████╗ ██╗   ██╗
████╗ ████║██║   ██║██║     ██╔══██╗██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝
██╔████╔██║██║   ██║██║     ██████╔╝█████╗  ██████╔╝██████╔╝ ╚████╔╝
██║╚██╔╝██║██║   ██║██║     ██╔══██╗██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝
██║ ╚═╝ ██║╚██████╔╝███████╗██████╔╝███████╗██║  ██║██║  ██║   ██║
╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝
```

**Mulberry** is a stock analysis platform that evaluates a company through **five complementary frameworks** and blends them into a single composite score and recommendation. It began as a Ben Graham value-investing tool (formerly *Charlotte*) and now goes well beyond classic value:

| Lens | Weight | What it measures |
|---|---|---|
| **Value** | 30% | Margin of safety from six intrinsic-value methods (Graham + DCF + DDM) |
| **Quality** | 25% | Margins, return on equity, free-cash-flow conversion and consistency |
| **Growth** | 20% | Revenue/EPS/FCF compounding, growth consistency, PEG (GARP) |
| **Momentum** | 15% | 50/200-day trend, RSI, 52-week range position, trailing returns |
| **Dividend** | 10% | Yield, payout sustainability, dividend growth, track record |

Dividend weight is redistributed for non-payers, and a severely negative margin of safety caps the recommendation at HOLD — quality alone never justifies buying at any price.

## Valuation Methods

1. **Graham Number** — `√(22.5 × EPS × BVPS)`
2. **Net-Net Working Capital (NCAV)** — liquidation floor at ⅔ discount
3. **Normalized Earnings** — multi-year average EPS × conservative P/E
4. **Growth-Adjusted Earnings** — `(EPS × (8.5 + 2g) × 4.4) / Y`
5. **Discounted Cash Flow** — two-stage FCF model (5-year capped growth + Gordon terminal value), with discount-rate/terminal-growth sensitivity grid
6. **Dividend Discount Model** — Gordon growth model for established payers

Plus the classic Graham **defensive investor checklist** (8 criteria) and **enterprising investor opportunity screen**.

## Reports

Self-contained HTML reports with interactive Plotly charts:

- Composite recommendation banner and 5-lens radar chart
- Intrinsic value estimates vs current price
- DCF summary with sensitivity table
- Margin-of-safety gauge
- 2-year price chart with 50/200-day moving averages
- Financial health scorecard and per-lens detail tables
- Revenue/net-income trends and key metrics

## Installation

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e .
```

No API keys required — all data comes from Yahoo Finance via `yfinance`.

## Usage

```bash
mulberry analyze AAPL             # full multi-framework report
mulberry analyze MSFT -o out.html -b   # custom path, open in browser
mulberry info                     # show configuration
mulberry test-api                 # verify Yahoo Finance connectivity
mulberry clear-cache [--all]      # cache maintenance
mulberry examples                 # usage examples
```

`fa` is available as a short alias for `mulberry`.

## Configuration

Optional — copy `config/.env.example` to `config/.env` to override defaults:

```bash
CACHE_TTL_QUOTES=300          # quote cache TTL (seconds)
CACHE_TTL_FUNDAMENTALS=86400  # fundamentals cache TTL
AAA_BOND_YIELD=5.0            # AAA yield used in growth-adjusted formula (%)
```

## Project Structure

```
mulberry/
├── api/               # Yahoo Finance wrapper
├── core/
│   ├── graham.py      # Graham valuation methods + checklists
│   ├── dcf.py         # Two-stage FCF discounted cash flow
│   ├── quality.py     # Business quality scoring
│   ├── growth.py      # Growth / GARP scoring
│   ├── dividend.py    # Dividend analysis + DDM
│   ├── technicals.py  # Momentum / technical scoring
│   ├── composite.py   # Weighted multi-framework blend
│   └── stock_analysis.py  # Data fetch + pipeline orchestration
├── cache/             # SQLite cache with TTL
├── visualization/     # Plotly chart builders
├── reports/           # HTML report generator
├── templates/         # Jinja2 templates
└── cli.py             # Click CLI
```

## Technology

Python 3.9+ · Click + Rich · yfinance · pandas · Plotly · Jinja2 · SQLAlchemy/SQLite

## Disclaimer

This tool is for educational and informational purposes only. It does not constitute financial, investment, or trading advice. Always conduct your own due diligence and consult a qualified financial advisor before making investment decisions. Past performance does not guarantee future results.

## References

- Graham, Benjamin. *The Intelligent Investor*. Harper Business, 1949.
- Graham, Benjamin & Dodd, David. *Security Analysis*. McGraw-Hill, 1934.
- Lynch, Peter. *One Up on Wall Street*. Simon & Schuster, 1989.
- Damodaran, Aswath. *Investment Valuation*. Wiley, 2012.
