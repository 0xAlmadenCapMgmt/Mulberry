"""
Glossary of Mulberry's technical terms and formulas.

A single, curated source of truth for every metric, ratio, valuation method,
and framework term that appears in a Mulberry report. It powers three surfaces:

  * the "Glossary & Formulas" section rendered into every HTML report,
  * inline hover tooltips on key terms throughout the report and web UI, and
  * the ``define_term`` tool the analysis agent uses to explain a term on request.

Definitions are plain text (no HTML) so the same entry renders safely as an HTML
tooltip, as a report table cell, and as plain text handed to the agent. Formulas
use unicode math symbols (√ × − ÷ ≤ ≥ Σ) which render cleanly in all three.
"""

from __future__ import annotations

import html as _html
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Category display order — groups terms the way a reader moves through a report.
CATEGORIES: Tuple[str, ...] = (
    "Core",
    "Valuation",
    "Frameworks & Lenses",
    "Quality",
    "Growth",
    "Dividend",
    "Momentum & Risk",
    "Peer & Forward",
    "SEC Filings",
    "Data Quality",
)


@dataclass(frozen=True)
class GlossaryTerm:
    """One glossary entry.

    Attributes:
        slug: stable, URL-safe identifier (e.g. ``margin-of-safety``).
        term: display name (e.g. ``Margin of Safety``).
        category: one of :data:`CATEGORIES`.
        definition: one- or two-sentence plain-language explanation.
        formula: optional plain-text formula (unicode math symbols).
        aliases: abbreviations / alternate names that should resolve here
            (e.g. ``("MoS",)``) — used for lookup and tooltip matching.
    """

    slug: str
    term: str
    category: str
    definition: str
    formula: str = ""
    aliases: Tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# The glossary. Keep entries grounded in what the report actually computes.
# ---------------------------------------------------------------------------

GLOSSARY: Tuple[GlossaryTerm, ...] = (
    # ── Core ────────────────────────────────────────────────────────────
    GlossaryTerm(
        "composite-score", "Composite Score", "Core",
        "Mulberry's headline 0–100 rating. A weighted blend of the five framework "
        "lens scores, where the weights come from the chosen investor profile. "
        "Higher is stronger on the balance of value, quality, growth, momentum, and dividend.",
        formula="Σ (lens score × lens weight)",
        aliases=("composite",),
    ),
    GlossaryTerm(
        "recommendation", "Recommendation", "Core",
        "The report's summary verdict (Strong Buy / Buy / Hold / Avoid), derived "
        "from the composite score and margin of safety. A severely negative margin "
        "of safety caps the recommendation at Hold regardless of the other lenses.",
    ),
    GlossaryTerm(
        "margin-of-safety", "Margin of Safety", "Core",
        "How far the current price sits below estimated intrinsic value — the buffer "
        "against estimation error. ≥30% is the classic value threshold; ≥50% is a deep-value situation.",
        formula="(Intrinsic Value − Market Price) ÷ Intrinsic Value",
        aliases=("MoS", "safety margin"),
    ),
    GlossaryTerm(
        "intrinsic-value", "Intrinsic Value", "Core",
        "An estimate of what a share is fundamentally worth, independent of its market "
        "price. Mulberry averages several valuation methods rather than trusting any single one.",
        aliases=("fair value", "avg intrinsic value"),
    ),

    # ── Valuation ───────────────────────────────────────────────────────
    GlossaryTerm(
        "graham-number", "Graham Number", "Valuation",
        "The highest price justified by earnings and book value together — the point "
        "where P/E ≤ 15 and P/B ≤ 1.5 hold simultaneously. A quick fair-value ceiling "
        "for a defensive stock.",
        formula="√(22.5 × EPS × Book Value per Share)",
        aliases=("earnings-book value", "graham number"),
    ),
    GlossaryTerm(
        "ncav", "Net Current Asset Value (NCAV)", "Valuation",
        "A liquidation-floor valuation: current assets minus all liabilities, per share. "
        "Buying below two-thirds of NCAV is Graham's deep-bargain signal — the market "
        "prices the business below its net liquid worth.",
        formula="(Current Assets − Total Liabilities) ÷ Shares",
        aliases=("NCAV", "net current asset value", "net asset value"),
    ),
    GlossaryTerm(
        "normalized-earnings-power", "Normalized Earnings Power", "Valuation",
        "Fair value based on multi-year average EPS rather than a single year, smoothing "
        "out cyclical earnings swings so the estimate isn't distorted by one boom or bust year.",
        formula="Avg EPS × (8.5 + 2g)",
    ),
    GlossaryTerm(
        "growth-adjusted-earnings", "Growth-Adjusted Earnings", "Valuation",
        "Graham's revised formula, adjusting fair value for expected growth and the "
        "prevailing AAA corporate bond yield so valuations move with interest rates.",
        formula="(EPS × (8.5 + 2g) × 4.4) ÷ Y",
        aliases=("dividend-adjusted value",),
    ),
    GlossaryTerm(
        "dcf", "Discounted Cash Flow (DCF)", "Valuation",
        "Values a company as the present value of its future free cash flows. Mulberry "
        "uses a conservative two-stage model: several years of capped growth, then a "
        "steady terminal growth rate.",
        formula="Σ FCFₜ ÷ (1+r)ᵗ + Terminal Value",
        aliases=("DCF", "discounted cash flow"),
    ),
    GlossaryTerm(
        "terminal-value", "Terminal Value", "Valuation",
        "The estimated value of all cash flows beyond the explicit forecast horizon, "
        "assuming the business settles into steady perpetual growth.",
        formula="FCF_final × (1 + g) ÷ (r − g)",
    ),
    GlossaryTerm(
        "discount-rate", "Discount Rate", "Valuation",
        "The annual rate used to convert future cash flows to today's value, reflecting "
        "the required return and risk. Higher discount rates lower the valuation.",
        aliases=("WACC",),
    ),
    GlossaryTerm(
        "terminal-growth", "Terminal Growth", "Valuation",
        "The perpetual growth rate assumed after the explicit DCF forecast — kept "
        "conservative (typically at or below long-run GDP growth) to avoid overvaluation.",
    ),
    GlossaryTerm(
        "ddm", "Dividend Discount Model (DDM)", "Valuation",
        "Values a dividend payer as the present value of its future dividends, growing "
        "steadily forever (the Gordon growth model). Meaningful only for established payers.",
        formula="D₁ ÷ (r − g)",
        aliases=("DDM", "gordon growth", "dividend discount"),
    ),
    GlossaryTerm(
        "ev-ebitda", "EV / EBITDA", "Valuation",
        "Enterprise value relative to operating cash earnings. A capital-structure-neutral "
        "valuation multiple, useful for comparing companies with different debt loads.",
        formula="Enterprise Value ÷ EBITDA",
        aliases=("EV/EBITDA",),
    ),
    GlossaryTerm(
        "ev-sales", "EV / Sales", "Valuation",
        "Enterprise value relative to revenue. A fallback multiple for companies with thin "
        "or negative earnings, where P/E and EV/EBITDA break down.",
        formula="Enterprise Value ÷ Revenue",
        aliases=("EV/Sales",),
    ),
    GlossaryTerm(
        "p-fcf", "Price / Free Cash Flow", "Valuation",
        "Market capitalization relative to free cash flow — how many dollars of price you "
        "pay per dollar of actual cash the business generates.",
        formula="Market Cap ÷ Free Cash Flow",
        aliases=("P/FCF", "price to fcf"),
    ),
    GlossaryTerm(
        "enterprise-value", "Enterprise Value (EV)", "Valuation",
        "The total value of a business to all capital providers: market cap plus net debt. "
        "What it would cost to buy the whole company, debt included.",
        formula="Market Cap + Total Debt − Cash",
        aliases=("EV", "enterprise value"),
    ),
    GlossaryTerm(
        "pe-ratio", "P/E Ratio", "Valuation",
        "Price-to-earnings: share price divided by earnings per share. How many dollars "
        "investors pay per dollar of annual profit. Mulberry's defensive target is ≤ 15x.",
        formula="Price ÷ EPS",
        aliases=("PE", "P/E", "price-to-earnings"),
    ),
    GlossaryTerm(
        "pb-ratio", "P/B Ratio", "Valuation",
        "Price-to-book: share price divided by book value per share. Below 1.5x is the "
        "classic value zone; the market prices the company near its net accounting worth.",
        formula="Price ÷ Book Value per Share",
        aliases=("PB", "P/B", "price-to-book"),
    ),
    GlossaryTerm(
        "eps", "Earnings per Share (EPS)", "Valuation",
        "Net income attributable to each share of common stock over the trailing twelve months. "
        "The per-share profit that anchors most valuation methods.",
        formula="Net Income ÷ Shares Outstanding",
        aliases=("EPS",),
    ),
    GlossaryTerm(
        "book-value", "Book Value per Share", "Valuation",
        "Shareholders' equity divided by shares outstanding — the per-share net accounting "
        "worth of the company if assets and liabilities were taken at balance-sheet value.",
        formula="Shareholders' Equity ÷ Shares",
        aliases=("BVPS", "book value"),
    ),
    GlossaryTerm(
        "fcf", "Free Cash Flow (FCF)", "Valuation",
        "Cash from operations after capital expenditures — the cash a business actually "
        "generates and can return to owners or reinvest. The fuel for the DCF model.",
        formula="Operating Cash Flow − Capital Expenditures",
        aliases=("FCF", "free cash flow"),
    ),

    # ── Frameworks & Lenses ─────────────────────────────────────────────
    GlossaryTerm(
        "value-lens", "Value Lens", "Frameworks & Lenses",
        "Scores how cheap the stock is versus its intrinsic value — the margin of safety "
        "from the Graham and DCF valuation methods. Default composite weight 30%.",
    ),
    GlossaryTerm(
        "quality-lens", "Quality Lens", "Frameworks & Lenses",
        "Scores business quality: profit margins, returns on equity, and how well earnings "
        "convert to cash. Default composite weight 25%.",
    ),
    GlossaryTerm(
        "growth-lens", "Growth Lens", "Frameworks & Lenses",
        "Scores revenue, EPS, and free-cash-flow compounding plus the PEG ratio — growth at "
        "a reasonable price. Default composite weight 20%.",
    ),
    GlossaryTerm(
        "momentum-lens", "Momentum Lens", "Frameworks & Lenses",
        "Scores price trend versus moving averages, RSI, and trailing returns. Default "
        "composite weight 15%.",
    ),
    GlossaryTerm(
        "dividend-lens", "Dividend Lens", "Frameworks & Lenses",
        "Scores dividend yield, payout sustainability, and track record. Default composite "
        "weight 10%, redistributed to the other lenses for non-payers.",
    ),
    GlossaryTerm(
        "investor-profile", "Investor Profile", "Frameworks & Lenses",
        "A named set of lens weights that tilts the composite toward a style: Balanced, "
        "Deep Value, GARP (growth at a reasonable price), Income, or Quality Growth. The "
        "report states which profile produced the score.",
        aliases=("profile", "weighting profile"),
    ),

    # ── Quality ─────────────────────────────────────────────────────────
    GlossaryTerm(
        "roe", "Return on Equity (ROE)", "Quality",
        "Net income as a percentage of shareholders' equity — how much profit the company "
        "generates on each dollar of owner capital. A core quality signal.",
        formula="Net Income ÷ Shareholders' Equity",
        aliases=("ROE", "return on equity"),
    ),
    GlossaryTerm(
        "current-ratio", "Current Ratio", "Quality",
        "Current assets divided by current liabilities — a liquidity check on whether the "
        "company can cover its near-term obligations. Mulberry's target is ≥ 2.0x.",
        formula="Current Assets ÷ Current Liabilities",
    ),
    GlossaryTerm(
        "debt-equity", "Debt / Equity", "Quality",
        "Total debt relative to shareholders' equity — a leverage gauge. Lower is safer; "
        "Mulberry's defensive target is < 0.5x.",
        formula="Total Debt ÷ Shareholders' Equity",
        aliases=("D/E", "debt to equity", "debt/equity"),
    ),
    GlossaryTerm(
        "cash-conversion", "Cash Conversion", "Quality",
        "How much of reported earnings turn into actual free cash flow. Consistently high "
        "conversion is a sign of earnings quality; persistently low conversion is a warning.",
        formula="Free Cash Flow ÷ Net Income",
    ),
    GlossaryTerm(
        "operating-margin", "Operating Margin", "Quality",
        "Operating income as a percentage of revenue — the profitability of the core "
        "business before interest and taxes.",
        formula="Operating Income ÷ Revenue",
        aliases=("margin", "operating margin"),
    ),

    # ── Growth ──────────────────────────────────────────────────────────
    GlossaryTerm(
        "cagr", "CAGR", "Growth",
        "Compound annual growth rate — the smoothed year-over-year rate at which a figure "
        "(revenue, EPS, FCF) grew over a multi-year period.",
        formula="(End ÷ Start)^(1÷years) − 1",
        aliases=("CAGR", "compound annual growth rate"),
    ),
    GlossaryTerm(
        "peg-ratio", "PEG Ratio", "Growth",
        "The P/E ratio divided by the earnings growth rate. Around 1.0 suggests growth is "
        "fairly priced; below 1.0 hints growth is available cheaply.",
        formula="P/E ÷ Earnings Growth Rate",
        aliases=("PEG", "forward PEG"),
    ),

    # ── Dividend ────────────────────────────────────────────────────────
    GlossaryTerm(
        "dividend-yield", "Dividend Yield", "Dividend",
        "Annual dividends per share as a percentage of the share price — the income return "
        "at today's price, before any price change.",
        formula="Annual Dividend ÷ Price",
        aliases=("yield",),
    ),
    GlossaryTerm(
        "payout-ratio", "Payout Ratio", "Dividend",
        "The share of earnings paid out as dividends. Low-to-moderate payout leaves room to "
        "sustain and grow the dividend; above ~80% raises sustainability questions.",
        formula="Dividends per Share ÷ EPS",
    ),

    # ── Momentum & Risk ─────────────────────────────────────────────────
    GlossaryTerm(
        "sma", "Moving Average (SMA)", "Momentum & Risk",
        "The average closing price over a trailing window (Mulberry uses 50- and 200-day). "
        "Price above a rising 200-day average is a classic uptrend signal.",
        aliases=("SMA", "50-day", "200-day", "moving average"),
    ),
    GlossaryTerm(
        "rsi", "Relative Strength Index (RSI)", "Momentum & Risk",
        "A 0–100 momentum oscillator. Above 70 is conventionally 'overbought', below 30 "
        "'oversold' — a gauge of how stretched a recent move is.",
        aliases=("RSI",),
    ),
    GlossaryTerm(
        "volatility", "Volatility (annualized)", "Momentum & Risk",
        "The annualized standard deviation of daily returns — how much the price swings. "
        "Higher volatility means a wider range of outcomes and larger drawdowns.",
        aliases=("volatility", "annualized volatility"),
    ),
    GlossaryTerm(
        "max-drawdown", "Maximum Drawdown", "Momentum & Risk",
        "The largest peak-to-trough decline over the measured period — the worst loss an "
        "investor holding through would have endured before a new high.",
        aliases=("drawdown", "max drawdown"),
    ),
    GlossaryTerm(
        "sharpe-ratio", "Sharpe Ratio", "Momentum & Risk",
        "Return earned per unit of risk taken — excess return over the risk-free rate "
        "divided by volatility. Higher is a better risk-adjusted result.",
        formula="(Return − Risk-Free Rate) ÷ Volatility",
        aliases=("sharpe",),
    ),
    GlossaryTerm(
        "beta", "Beta", "Momentum & Risk",
        "How much the stock moves relative to the broad market. Beta 1.0 moves with the "
        "market; above 1.0 amplifies market moves, below 1.0 dampens them.",
        aliases=("beta",),
    ),

    # ── Peer & Forward ──────────────────────────────────────────────────
    GlossaryTerm(
        "percentile", "Percentile (Peer-Relative)", "Peer & Forward",
        "The share of the peer set the target beats on a given metric. An 80th-percentile "
        "margin means the company's margin exceeds 80% of its peers — context beats a fixed threshold.",
        aliases=("pct", "percentile"),
    ),
    GlossaryTerm(
        "peer-median", "Peer Median", "Peer & Forward",
        "The middle value of a metric across the peer set — a robust benchmark the target is "
        "compared against, less distorted by outliers than an average.",
    ),
    GlossaryTerm(
        "forward-pe", "Forward P/E", "Peer & Forward",
        "Price divided by expected next-twelve-months earnings rather than trailing earnings "
        "— the market's forward valuation. Shown as context; it does not feed the composite score.",
        aliases=("forward P/E",),
    ),
    GlossaryTerm(
        "analyst-consensus", "Analyst Consensus", "Peer & Forward",
        "The aggregated recommendation of covering sell-side analysts, often as a 1–5 mean "
        "(1 = strong buy). Context only — Mulberry's scores are computed independently.",
        aliases=("recommendation mean", "consensus"),
    ),
    GlossaryTerm(
        "price-target", "Price Target", "Peer & Forward",
        "Analysts' estimated fair price over the next ~12 months (mean, with a low–high range). "
        "Noisy forward context that does not feed the composite score.",
        aliases=("target price", "mean price target"),
    ),

    # ── SEC Filings ─────────────────────────────────────────────────────
    GlossaryTerm(
        "red-flag", "Red Flag", "SEC Filings",
        "A material warning detected in recent SEC filings — going-concern language, a "
        "material-weakness disclosure, a restatement, or a notable 8-K event — each tagged "
        "by severity. Context only; red flags never change the numeric scores.",
        aliases=("red flags",),
    ),
    GlossaryTerm(
        "going-concern", "Going-Concern Doubt", "SEC Filings",
        "An explicit disclosure that substantial doubt exists about the company's ability to "
        "continue operating for the next year — one of the most serious filing red flags.",
    ),
    GlossaryTerm(
        "material-weakness", "Material Weakness", "SEC Filings",
        "A deficiency in internal control over financial reporting serious enough that a "
        "misstatement could go undetected — it undermines confidence in the reported numbers.",
    ),
    GlossaryTerm(
        "restatement", "Restatement", "SEC Filings",
        "A formal correction of previously issued financial statements (flagged via 8-K "
        "Item 4.02) — prior figures were unreliable and have been revised.",
    ),
    GlossaryTerm(
        "filing-freshness", "Filing Freshness", "SEC Filings",
        "How many days have passed since the company's most recent periodic (10-K/10-Q) "
        "filing — a staleness check on how current the filing-based context is.",
        aliases=("freshness", "days since last periodic"),
    ),
    GlossaryTerm(
        "mdna", "MD&A", "SEC Filings",
        "Management's Discussion & Analysis — the narrative section of a 10-K/10-Q where "
        "management explains results and outlook in its own words.",
        aliases=("MD&A", "management discussion"),
    ),

    # ── Data Quality ────────────────────────────────────────────────────
    GlossaryTerm(
        "data-confidence", "Data Confidence", "Data Quality",
        "A High / Medium / Low badge measuring how much of each framework's required input "
        "was actually available from the data source. It rates data completeness, not "
        "investment merit — a low-confidence score leans on missing or zero-filled inputs.",
        aliases=("confidence",),
    ),
)


# ---------------------------------------------------------------------------
# Lookup helpers (pure — unit-tested directly)
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Normalize a term for matching: lowercase, collapse non-alphanumerics."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# term/alias (normalized) -> GlossaryTerm, built once at import.
_INDEX: Dict[str, GlossaryTerm] = {}
for _t in GLOSSARY:
    _INDEX[_norm(_t.term)] = _t
    _INDEX[_norm(_t.slug)] = _t
    for _a in _t.aliases:
        _INDEX.setdefault(_norm(_a), _t)


def all_terms() -> Tuple[GlossaryTerm, ...]:
    """Every glossary term, in definition order."""
    return GLOSSARY


def by_category() -> "OrderedDict[str, List[GlossaryTerm]]":
    """Terms grouped by category, in :data:`CATEGORIES` order, terms alphabetical."""
    grouped: "OrderedDict[str, List[GlossaryTerm]]" = OrderedDict(
        (cat, []) for cat in CATEGORIES
    )
    for term in GLOSSARY:
        grouped.setdefault(term.category, []).append(term)
    for terms in grouped.values():
        terms.sort(key=lambda t: t.term.lower())
    # Drop any category that ended up empty.
    return OrderedDict((c, ts) for c, ts in grouped.items() if ts)


def lookup(query: str) -> Optional[GlossaryTerm]:
    """Resolve a query to a term by slug, display name, or alias (case-insensitive).

    Falls back to a unique substring match so ``"sharpe"`` finds "Sharpe Ratio".
    Returns None if there's no match or the substring is ambiguous.
    """
    if not query:
        return None
    key = _norm(query)
    if key in _INDEX:
        return _INDEX[key]
    # Unique substring fallback, but only for keys long enough that a substring
    # match is meaningful — avoids short aliases matching inside unrelated words.
    if len(key) < 4:
        return None
    hits = {
        t.slug: t
        for k, t in _INDEX.items()
        if len(k) >= 4 and (key in k or k in key)
    }
    if len(hits) == 1:
        return next(iter(hits.values()))
    return None


def tooltip_for(display: str) -> Optional[str]:
    """The definition string to show when hovering ``display``, or None."""
    term = lookup(display)
    return term.definition if term else None


def annotate(display: str, key: Optional[str] = None) -> str:
    """Wrap ``display`` in a hover-tooltip span if it maps to a glossary term.

    ``key`` overrides what is looked up (use it when the visible text differs
    from the term name). Returns an HTML-safe string: if no term matches, the
    display text is returned escaped and unwrapped. The ``.gloss`` class is
    styled in the report and web base templates.
    """
    term = lookup(key or display)
    safe_display = _html.escape(str(display))
    if term is None:
        return safe_display
    tip = _html.escape(term.definition, quote=True)
    return (
        f'<span class="gloss" tabindex="0" data-tip="{tip}">'
        f"{safe_display}</span>"
    )
