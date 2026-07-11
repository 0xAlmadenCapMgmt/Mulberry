# Mulberry Roadmap

Mulberry is a multi-framework stock-analysis tool: it blends value, quality,
growth, dividend, and momentum lenses into a composite score and renders an
interactive HTML report from Yahoo Finance data.

This roadmap takes it from a working report generator to a trustworthy,
research-grade capability. The primary use case driving priorities is **deep
single-name research**, so the sequence front-loads trustworthiness, then
deepens single-name signal, adds temporal/qualitative context from filings,
layers on narrative synthesis, and finishes with universe screening. A guiding
principle throughout: analyses should be **contextualized across past, present,
and future**, not resting on point-in-time snapshots. Each phase is
independently shippable.

**Status legend:** ✅ done · 🔜 next · ⬜ planned

| Phase | Theme | Target version | Status |
|-------|-------|----------------|--------|
| 1 | Trust & Foundation | 0.4.0 | ✅ Complete |
| 2 | Sharper Signal | 0.5.0 | ✅ Complete |
| 3 | SEC Filings & Temporal Context | 0.6.0 | 🔜 Next |
| 4 | AI Thesis Layer | 0.7.0 | ⬜ Planned |
| 5 | Screening & Portfolio | 0.8.0 | ⬜ Planned |

---

## Phase 1 — Trust & Foundation ✅ (v0.4.0)

Make the numbers verifiable and the data honest; remove dead weight. Everything
else builds on this.

- **Test suite & CI** — `tests/` with ~96 fully-offline tests (exact
  golden-value tests on every valuation formula; behavioral tests on the scoring
  aggregations; a patched-yfinance fixture that runs the whole pipeline and
  report render with no network). GitHub Actions runs pytest on Python 3.9–3.11.
- **Data-confidence scoring** — `core/data_quality.py` measures how much required
  input each lens actually had; the report shows a High/Medium/Low badge and a
  per-lens breakdown so scores built on missing data are flagged, not silently
  trusted.
- **Consolidated data path + real caching** — a single Yahoo access path
  (`YahooFinanceAPI.get_raw_bundle`) and a pickle-backed `RawDataCache` that
  serves repeat runs from disk (~2.6s → ~0.9s). Sharpe / volatility / max-drawdown
  now feed the momentum lens and the report.
- **Correctness fix** — dividend-yield units (yfinance now reports percent-units;
  prefer `trailingAnnualDividendYield`).
- **Dead-code removal** — deleted the unreferenced `api/base.py` and the entire
  vestigial SQLite cache subsystem; dropped the `sqlalchemy` dependency.

Delivered on branch `phase1-trust-foundation`.

---

## Phase 2 — Sharper Signal ✅ (v0.5.0)

Replace blunt absolute thresholds with context, and add the missing valuation
and forward-looking dimensions — the highest-leverage work for deep single-name
research.

1. **Peer-relative scoring** — new `core/relative.py`. Accept an explicit peer
   set via `analyze --peers T1,T2,...`, fetch each peer's key metrics, and
   compute the target's percentile rank per metric (margins, ROE, growth,
   EV/EBITDA, P/E, …). New "Peer-Relative" report section (target vs peer median
   and percentile). A 12% operating margin means very different things in
   software vs grocery — this makes every lens sector-aware.
2. **Relative-valuation multiples** — add EV/EBITDA, EV/Sales, and P/FCF to the
   value metrics (using enterprise value, EBITDA, revenue, and FCF), currently
   absent from the Graham-style absolute view.
3. **Forward-looking context** — surface analyst recommendations, forward P/E,
   and forward PEG as a context panel. Estimates inform but do not drive the
   composite score unless explicitly flagged.
4. **Investor-style weight profiles** — replace the hardcoded composite weights
   with named profiles (`balanced`, `deep_value`, `garp`, `income`,
   `quality_growth`) selectable via `analyze --profile NAME`; the report states
   which profile was used.

**Verification:** `analyze KO --peers PEP,KDP,MNST` renders percentiles and the
new multiples; `analyze AAPL --profile deep_value` visibly shifts the weights and
composite; sanity-check a dividend payer (KO), a non-payer growth name (PLTR),
and a mega-cap (AAPL).

Delivered on branch `phase2-sharper-signal`: `core/relative.py` (percentile
ranking), `core/multiples.py`, `core/forward.py`, five named weight profiles in
`core/composite.py`, and `analyze --peers/--profile`.

---

## Phase 3 — SEC Filings & Temporal Context ⬜ (v0.6.0)

Add SEC EDGAR as a second data source so analyses rest on trajectory and
narrative, not a single yfinance snapshot. Filings provide **context and
explicit flags only — they never change the composite score.** EDGAR is free and
needs only a `User-Agent` header (no API key); `config.sec_user_agent` already
exists.

- **Structured XBRL history** — new `api/sec_edgar.py` + `core/filings.py` pull
  ~5-year time series of debt, liabilities, cash & float, assets, equity, shares
  (dilution vs buyback), revenue, and capex/investment from EDGAR `companyfacts`,
  and derive plain-language trend signals (leverage rising/falling, cash trend).
- **Filing timeline + red flags** — recent 10-K/10-Q/8-K dates, a freshness
  signal, material-event detection, and a keyword/8-K-item scan for
  going-concern, material-weakness, restatement, and debt-covenant language, each
  with a severity.
- **Qualitative sections** — extract MD&A and Risk-Factor text from the latest
  10-K/10-Q, surfaced as collapsible excerpts. This phase *extracts and displays*
  them; their LLM *synthesis* is handed to Phase 4.
- Renders a "SEC Filings & Trends" report section (timeline, debt/cash/shares
  trend charts, red-flag callout, excerpts); a 7-day-TTL filings cache keeps
  repeat runs fast. Degrades gracefully — if EDGAR is unavailable the section is
  omitted and the rest of the report is unaffected.

---

## Phase 4 — AI Thesis Layer ⬜ (v0.7.0)

Turn the computed metrics — and the Phase 3 filing text — into a written thesis
for research notes.

- New `ai/thesis.py` calls the Anthropic (Claude) API with the composite score,
  per-lens scores/verdicts, key metrics, and the **extracted MD&A / Risk-Factor
  text and red flags from Phase 3**, returning a narrative thesis, bull case,
  bear case, and flagged risks — synthesizing the "leadership vision / company
  health" reading the raw filings can't give on their own.
- Renders as an "Investment Thesis (AI-generated)" report section with a clear
  model-generated disclaimer. It is advisory/narrative only — it never alters the
  numeric scores or the recommendation.
- Requires an optional `ANTHROPIC_API_KEY`; degrades gracefully (section omitted)
  when absent, so the tool still runs without a key.

---

## Phase 5 — Screening & Portfolio ⬜ (v0.8.0)

Scale trustworthy single-name analysis to a universe.

- `screen T1 T2 ...` / `--universe file.txt` runs analysis per ticker and outputs
  a ranked comparison (HTML + CSV) sorted by composite score, honoring
  `--profile`.
- Filing-derived signals (leverage trend, filing freshness, red flags) become
  screen columns and filters, letting the temporal context from Phase 3 drive
  candidate surfacing.
- Watchlist / score history: persist composite + lens scores per symbol per run
  date, enabling score-over-time sparklines on the single-name report.

---

## Design principles

- **Data honesty over false precision** — a score is only as good as its inputs;
  surface confidence rather than hide gaps.
- **Reproducible and offline-testable** — every formula has a golden-value test;
  the suite runs with no network.
- **Educational, not advisory** — Mulberry informs research; it does not give
  personalized investment advice, and the disclaimer stays.
- **Each phase ships on its own** — no phase depends on a later one being built.
