"""
SEC filings analysis — temporal and qualitative context

Mulberry's other lenses read a point-in-time yfinance snapshot. This engine adds
the trajectory and the narrative from SEC EDGAR filings:

- a **filing timeline** (recent 10-K/10-Q/8-K, freshness, material events),
- **structured multi-year trends** from XBRL company facts (debt, liabilities,
  cash, assets, equity, shares, revenue, net income),
- a **red-flag scan** (going-concern / material-weakness / restatement language,
  notable 8-K item codes, and a derived "leverage up while cash down" signal),
- **qualitative excerpts** (MD&A and Risk Factors) surfaced for reading now and
  for LLM synthesis in a later phase.

Filings are **context and flags only — they never change the composite score.**
Everything degrades gracefully: if EDGAR can't be reached or the ticker can't be
resolved, ``analyze`` returns ``None`` and the rest of the report is unaffected.
"""

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FilingRef:
    form: str
    filing_date: str
    report_date: str
    accession: str
    primary_document: str
    items: str = ""            # 8-K item codes, comma-separated


@dataclass
class TrendSeries:
    label: str
    unit: str                  # "USD" | "shares"
    higher_is_better: bool
    points: List[Tuple[str, float]]   # (period_end, value), oldest -> newest
    latest: float
    earliest: float
    change_pct: float
    direction: str             # Rising / Falling / Flat


@dataclass
class RedFlag:
    label: str
    severity: str              # high / medium / info
    detail: str = ""


@dataclass
class QualitativeSection:
    title: str
    excerpt: str


@dataclass
class FilingsAssessment:
    cik: str
    entity_name: str = ""
    latest_10k: Optional[FilingRef] = None
    latest_10q: Optional[FilingRef] = None
    days_since_last_periodic: Optional[int] = None
    recent_8k_count: int = 0
    timeline: List[FilingRef] = field(default_factory=list)
    trends: List[TrendSeries] = field(default_factory=list)
    red_flags: List[RedFlag] = field(default_factory=list)
    sections: List[QualitativeSection] = field(default_factory=list)
    available: bool = True


# ---------------------------------------------------------------------------
# Concept specs & flag maps
# ---------------------------------------------------------------------------

# (label, [us-gaap tags in preference order], unit, higher_is_better)
_CONCEPTS: List[Tuple[str, List[str], str, bool]] = [
    ("Total liabilities", ["Liabilities"], "USD", False),
    ("Long-term debt", ["LongTermDebtNoncurrent", "LongTermDebt"], "USD", False),
    ("Cash & equivalents", ["CashAndCashEquivalentsAtCarryingValue"], "USD", True),
    ("Total assets", ["Assets"], "USD", True),
    ("Shareholders' equity", ["StockholdersEquity"], "USD", True),
    ("Shares outstanding", ["CommonStockSharesOutstanding"], "shares", False),
    ("Revenue", ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"], "USD", True),
    ("Net income", ["NetIncomeLoss"], "USD", True),
]

# Words that negate a nearby risk phrase ("no substantial doubt", "did not ...").
# Used to avoid false positives from boilerplate that healthy filings all carry.
_NEGATIONS = ("no ", "not ", "n't", "any ", "without ", "free of", "absence of")

_ITEM_FLAGS: Dict[str, Tuple[str, str]] = {
    "4.02": ("high", "Non-reliance on previously issued financial statements (restatement)"),
    "1.03": ("high", "Bankruptcy or receivership"),
    "2.04": ("medium", "Triggering event accelerating a financial obligation"),
    "2.06": ("medium", "Material impairment"),
    "5.02": ("info", "Departure or appointment of directors/officers"),
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested directly)
# ---------------------------------------------------------------------------

def html_to_text(raw: str) -> str:
    """Strip tags/entities from filing HTML to searchable plain text."""
    if not raw:
        return ""
    cleaned = _SCRIPT_STYLE_RE.sub(" ", raw)
    cleaned = _TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    # Normalize typographic punctuation so heading/keyword matching is reliable
    # (real filings use curly apostrophes, e.g. "Management’s Discussion").
    cleaned = cleaned.replace("’", "'").replace("‘", "'")
    cleaned = cleaned.replace("“", '"').replace("”", '"')
    return _WS_RE.sub(" ", cleaned).strip()


def extract_annual_series(
    facts: Dict[str, Any], tags: List[str], unit: str, max_points: int = 5
) -> List[Tuple[str, float]]:
    """Pull an annual (period_end, value) series for the first matching tag.

    Uses annual (10-K / fiscal-year) data points only, deduped by period end
    (keeping the most recently reported value), sorted oldest -> newest.
    """
    gaap = (facts or {}).get("facts", {}).get("us-gaap", {})
    for tag in tags:
        concept = gaap.get(tag)
        if not concept:
            continue
        points = concept.get("units", {}).get(unit)
        if not points:
            continue
        by_end: Dict[str, float] = {}
        for p in points:
            form = p.get("form", "")
            fp = p.get("fp", "")
            if not (form.startswith("10-K") or fp == "FY"):
                continue
            end = p.get("end")
            val = p.get("val")
            if end is None or val is None:
                continue
            by_end[end] = float(val)   # later entries overwrite -> most recent
        if by_end:
            ordered = sorted(by_end.items())
            return ordered[-max_points:]
    return []


def _direction(change_pct: float) -> str:
    if change_pct > 0.05:
        return "Rising"
    if change_pct < -0.05:
        return "Falling"
    return "Flat"


def build_trend(
    label: str, unit: str, higher_is_better: bool,
    series: List[Tuple[str, float]],
) -> Optional[TrendSeries]:
    """Turn a raw series into a TrendSeries, or None if too short."""
    if len(series) < 2:
        return None
    earliest = series[0][1]
    latest = series[-1][1]
    change_pct = (latest - earliest) / abs(earliest) if earliest else 0.0
    return TrendSeries(
        label=label,
        unit=unit,
        higher_is_better=higher_is_better,
        points=series,
        latest=latest,
        earliest=earliest,
        change_pct=change_pct,
        direction=_direction(change_pct),
    )


def text_red_flags(text: str) -> List["RedFlag"]:
    """High-precision red flags from filing prose.

    Deliberately conservative: only the SEC going-concern trigger
    ("substantial doubt ... going concern"), with a negation guard so the
    ubiquitous "no substantial doubt" boilerplate does not fire. Material
    weaknesses and restatements are intentionally NOT keyword-scanned — the
    term appears in every filing's control definitions and comparability notes,
    so they are surfaced via 8-K item codes (e.g. 4.02) instead, and the raw
    text is left for the qualitative excerpts / later LLM synthesis.
    """
    low = text.lower()
    for m in re.finditer(r"substantial doubt", low):
        pre = low[max(0, m.start() - 20):m.start()]
        if any(neg in pre for neg in _NEGATIONS):
            continue
        post = low[m.end():m.end() + 90]
        if "going concern" in post or "continue as a going" in post:
            return [RedFlag(
                label="Going concern",
                severity="high",
                detail="Substantial-doubt / going-concern language disclosed",
            )]
    return []


def extract_section(text: str, heading: str, length: int = 1200) -> Optional[str]:
    """Best-effort excerpt of a named section from filing text.

    Uses the *last* occurrence of the heading, since the first is usually the
    table-of-contents entry rather than the section body.
    """
    if not text:
        return None
    idx = text.lower().rfind(heading.lower())
    if idx == -1:
        return None
    start = idx + len(heading)
    excerpt = text[start:start + length].strip(" .:—-")
    if len(excerpt) < 100:
        return None
    if len(text) > start + length:
        excerpt += " …"
    return excerpt


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class FilingsAnalyzer:
    """Builds a FilingsAssessment for a ticker from an EDGAR client."""

    def __init__(self, client=None, cache=None):
        # Lazy import keeps `requests` off the import path for pure-logic users.
        if client is None:
            from ..api.sec_edgar import SECEdgarClient
            client = SECEdgarClient()
        self.client = client
        self.cache = cache

    def analyze(self, ticker: str) -> Optional[FilingsAssessment]:
        ticker = ticker.upper()
        if self.cache is not None:
            cached = self.cache.get(ticker)
            if cached is not None:
                return cached

        cik = self.client.resolve_cik(ticker)
        if cik is None:
            logger.info(f"No SEC CIK for {ticker}; skipping filings analysis")
            return None

        submissions = self.client.get_submissions(cik)
        facts = self.client.get_company_facts(cik)
        if submissions is None and facts is None:
            logger.info(f"No SEC data reachable for {ticker}")
            return None

        entity_name = (submissions or {}).get("name", "") or (facts or {}).get("entityName", "")
        timeline, latest_10k, latest_10q, freshness, count_8k = self._parse_timeline(submissions)
        trends = self._build_trends(facts)

        # Fetch the most recent periodic filing text once, for flags + excerpts.
        latest_periodic = latest_10k or latest_10q
        text = ""
        if latest_periodic is not None:
            raw = self.client.get_filing_document(
                cik, latest_periodic.accession, latest_periodic.primary_document
            )
            text = html_to_text(raw) if raw else ""

        red_flags = self._scan_red_flags(text, timeline, trends)
        sections = self._extract_sections(text)

        assessment = FilingsAssessment(
            cik=cik,
            entity_name=entity_name,
            latest_10k=latest_10k,
            latest_10q=latest_10q,
            days_since_last_periodic=freshness,
            recent_8k_count=count_8k,
            timeline=timeline,
            trends=trends,
            red_flags=red_flags,
            sections=sections,
            available=True,
        )

        if self.cache is not None:
            self.cache.set(ticker, assessment)
        return assessment

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_timeline(submissions: Optional[Dict[str, Any]]):
        """Return (timeline, latest_10k, latest_10q, days_since_periodic, 8k_count)."""
        if not submissions:
            return [], None, None, None, 0
        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        accns = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        items = recent.get("items", [])

        def at(seq, i):
            return seq[i] if i < len(seq) else ""

        timeline: List[FilingRef] = []
        latest_10k = latest_10q = None
        count_8k = 0
        today = datetime.now().date()

        for i, form in enumerate(forms):
            ref = FilingRef(
                form=form,
                filing_date=at(dates, i),
                report_date=at(report_dates, i),
                accession=at(accns, i),
                primary_document=at(docs, i),
                items=at(items, i),
            )
            if form.startswith("10-K") and latest_10k is None:
                latest_10k = ref
            elif form.startswith("10-Q") and latest_10q is None:
                latest_10q = ref

            if form == "8-K":
                if _within_days(ref.filing_date, today, 365):
                    count_8k += 1

            if form in ("10-K", "10-Q", "8-K") and len(timeline) < 12:
                timeline.append(ref)

        freshness = None
        periodic_dates = [
            r.filing_date for r in (latest_10k, latest_10q) if r and r.filing_date
        ]
        if periodic_dates:
            most_recent = max(_parse_date(d) for d in periodic_dates)
            if most_recent:
                freshness = (today - most_recent).days

        return timeline, latest_10k, latest_10q, freshness, count_8k

    @staticmethod
    def _build_trends(facts: Optional[Dict[str, Any]]) -> List[TrendSeries]:
        if not facts:
            return []
        trends = []
        for label, tags, unit, higher_is_better in _CONCEPTS:
            series = extract_annual_series(facts, tags, unit)
            trend = build_trend(label, unit, higher_is_better, series)
            if trend is not None:
                trends.append(trend)
        return trends

    @staticmethod
    def _scan_red_flags(
        text: str, timeline: List[FilingRef], trends: List[TrendSeries]
    ) -> List[RedFlag]:
        flags: List[RedFlag] = []
        seen = set()

        for flag in text_red_flags(text):
            flags.append(flag)
            seen.add(flag.detail)

        # 8-K material-event item codes (recent filings only)
        for ref in timeline:
            if ref.form != "8-K" or not ref.items:
                continue
            for code in [c.strip() for c in ref.items.split(",")]:
                if code in _ITEM_FLAGS and code not in seen:
                    severity, detail = _ITEM_FLAGS[code]
                    flags.append(RedFlag(
                        label=f"8-K Item {code}", severity=severity,
                        detail=f"{detail} (filed {ref.filing_date})",
                    ))
                    seen.add(code)

        # Derived: leverage rising sharply while cash falls. Prefer long-term
        # debt (the sharper leverage signal), falling back to total liabilities.
        by_label = {t.label: t for t in trends}
        debt = by_label.get("Long-term debt") or by_label.get("Total liabilities")
        cash = by_label.get("Cash & equivalents")
        if debt and cash and debt.change_pct > 0.20 and cash.change_pct < -0.10:
            flags.append(RedFlag(
                label="Leverage up, cash down", severity="medium",
                detail=f"{debt.label} {debt.change_pct:+.0%} while cash {cash.change_pct:+.0%} over the period",
            ))

        return flags

    @staticmethod
    def _extract_sections(text: str) -> List[QualitativeSection]:
        sections = []
        for title, heading in (
            ("Management's Discussion & Analysis", "Management's Discussion and Analysis"),
            ("Risk Factors", "Risk Factors"),
        ):
            excerpt = extract_section(text, heading)
            if excerpt:
                sections.append(QualitativeSection(title=title, excerpt=excerpt))
        return sections


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _within_days(date_str: str, reference, days: int) -> bool:
    d = _parse_date(date_str)
    if d is None:
        return False
    return 0 <= (reference - d).days <= days
