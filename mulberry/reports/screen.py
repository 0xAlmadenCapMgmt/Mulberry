"""
Universe screening — ranked multi-ticker comparison

Runs the full single-name analysis pipeline for each ticker and produces a
comparison ranked by composite score, as both an HTML report and a CSV.
Honors the selected investor-style weight profile; optionally includes
filing-derived signals (red-flag count, leverage trend) as screen columns.
"""

import asyncio
import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import jinja2

from ..core.stock_analysis import StockAnalyzer
from ..cache.history import ScoreHistory, snapshot_from_analysis
from ..utils.logger import get_logger
from ..utils.config import config
from ..utils.formatters import format_currency, format_percent

logger = get_logger(__name__)


@dataclass
class ScreenRow:
    """One ranked line of the screen."""
    symbol: str
    name: str = ""
    price: float = 0.0
    composite: float = 0.0
    recommendation: str = ""
    lens_scores: Dict[str, float] = field(default_factory=dict)
    margin_of_safety: float = 0.0
    pe_ratio: float = 0.0
    confidence: str = ""
    red_flag_count: Optional[int] = None     # None when filings not requested
    leverage_trend: str = ""
    error: str = ""                           # non-empty when analysis failed


class Screener:
    """Runs the analysis pipeline across a ticker universe and ranks it."""

    def __init__(
        self,
        profile: str = "balanced",
        include_filings: bool = False,
        analyzer: Optional[StockAnalyzer] = None,
        history: Optional[ScoreHistory] = None,
    ):
        self.profile = profile
        self.include_filings = include_filings
        self.analyzer = analyzer or StockAnalyzer(profile=profile)
        self.history = history or ScoreHistory()

    async def run(self, symbols: List[str]) -> List[ScreenRow]:
        """Analyze every symbol (failures become error rows) and rank."""
        seen = set()
        unique = [s.upper() for s in symbols
                  if s.upper() not in seen and not seen.add(s.upper())]

        rows = await asyncio.gather(*(self._analyze_one(s) for s in unique))

        ranked = sorted(
            [r for r in rows if not r.error],
            key=lambda r: r.composite, reverse=True,
        )
        failed = [r for r in rows if r.error]
        return ranked + failed

    async def _analyze_one(self, symbol: str) -> ScreenRow:
        try:
            analysis = await self.analyzer.analyze(
                symbol, include_filings=self.include_filings
            )
        except Exception as e:
            logger.warning(f"Screen: {symbol} failed — {e}")
            return ScreenRow(symbol=symbol, error=str(e))

        self.history.record(symbol, snapshot_from_analysis(analysis))
        return build_row(symbol, analysis, self.include_filings)


def build_row(symbol: str, analysis: Dict[str, Any], include_filings: bool) -> ScreenRow:
    """Distill an analysis result into a screen row (pure)."""
    composite = analysis["frameworks"]["composite"]
    confidence = analysis.get("data_confidence")
    margins = analysis.get("valuation", {}).get("margins_of_safety", {})

    row = ScreenRow(
        symbol=symbol,
        name=analysis.get("company_info", {}).get("name", symbol),
        price=analysis.get("current_price", 0),
        composite=composite.overall_score,
        recommendation=analysis.get("recommendation", ""),
        lens_scores=dict(composite.lens_scores),
        margin_of_safety=margins.get("average", 0),
        pe_ratio=analysis.get("metrics", {}).get("pe_ratio", 0),
        confidence=confidence.level if confidence else "",
    )

    if include_filings:
        filings = analysis.get("filings")
        if filings is not None:
            row.red_flag_count = len(filings.red_flags)
            debt = next(
                (t for t in filings.trends
                 if t.label in ("Long-term debt", "Total liabilities")),
                None,
            )
            row.leverage_trend = debt.direction if debt else ""
        else:
            row.red_flag_count = None
            row.leverage_trend = "n/a"

    return row


class ScreenReportGenerator:
    """Renders a ranked screen as HTML (+ CSV alongside)."""

    def __init__(self, screener: Optional[Screener] = None, profile: str = "balanced",
                 include_filings: bool = False):
        self.screener = screener or Screener(profile=profile, include_filings=include_filings)
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(config.templates_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.jinja_env.filters["currency"] = format_currency
        self.jinja_env.filters["percent"] = format_percent

    async def generate(
        self, symbols: List[str], output_path: Optional[str] = None
    ) -> str:
        rows = await self.screener.run(symbols)

        if output_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = config.output_dir / f"screen_{stamp}.html"
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html = self.jinja_env.get_template("screen.html").render(
            rows=rows,
            profile=self.screener.profile,
            include_filings=self.screener.include_filings,
            generation_time=datetime.now().strftime("%B %d, %Y %H:%M"),
            analyzed=len([r for r in rows if not r.error]),
            failed=len([r for r in rows if r.error]),
        )
        output_path.write_text(html, encoding="utf-8")

        csv_path = output_path.with_suffix(".csv")
        write_csv(rows, csv_path, self.screener.include_filings)

        logger.info(f"Screen saved: {output_path} (+ {csv_path.name})")
        return str(output_path)


def write_csv(rows: List[ScreenRow], path, include_filings: bool) -> None:
    """Write the ranked screen to CSV."""
    fields = [
        "rank", "symbol", "name", "price", "composite", "recommendation",
        "value", "quality", "growth", "momentum", "dividend",
        "margin_of_safety", "pe_ratio", "confidence",
    ]
    if include_filings:
        fields += ["red_flags", "leverage_trend"]
    fields.append("error")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(rows, start=1):
            record = {
                "rank": i if not row.error else "",
                "symbol": row.symbol,
                "name": row.name,
                "price": f"{row.price:.2f}",
                "composite": f"{row.composite:.0f}",
                "recommendation": row.recommendation,
                "value": f"{row.lens_scores.get('value', 0):.0f}",
                "quality": f"{row.lens_scores.get('quality', 0):.0f}",
                "growth": f"{row.lens_scores.get('growth', 0):.0f}",
                "momentum": f"{row.lens_scores.get('momentum', 0):.0f}",
                "dividend": f"{row.lens_scores.get('dividend', 0):.0f}",
                "margin_of_safety": f"{row.margin_of_safety:.3f}",
                "pe_ratio": f"{row.pe_ratio:.1f}",
                "confidence": row.confidence,
                "error": row.error,
            }
            if include_filings:
                record["red_flags"] = "" if row.red_flag_count is None else row.red_flag_count
                record["leverage_trend"] = row.leverage_trend
            writer.writerow(record)
