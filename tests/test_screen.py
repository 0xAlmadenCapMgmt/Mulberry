"""Tests for Phase 5: score history, screener, and the screen report."""

import asyncio
import csv

import pytest

from mulberry.cache.history import ScoreHistory, snapshot_from_analysis
from mulberry.core.stock_analysis import StockAnalyzer
from mulberry.core.filings import FilingsAnalyzer
from mulberry.reports.screen import (
    Screener, ScreenReportGenerator, ScreenRow, build_row, write_csv,
)
from mulberry.reports.generator import ReportGenerator
from mulberry.visualization.charts import ChartBuilder


# --- ScoreHistory ------------------------------------------------------------

def test_history_round_trip(tmp_path):
    h = ScoreHistory(tmp_path, disabled=False)
    h.record("TEST", {"composite": 55.0, "price": 100.0})
    entries = h.load("TEST")
    assert len(entries) == 1
    assert entries[0]["composite"] == 55.0
    assert "date" in entries[0]


def test_history_one_entry_per_day(tmp_path):
    h = ScoreHistory(tmp_path, disabled=False)
    h.record("TEST", {"composite": 50.0})
    h.record("TEST", {"composite": 60.0})   # same day — replaces
    entries = h.load("TEST")
    assert len(entries) == 1
    assert entries[0]["composite"] == 60.0


def test_history_disabled_noop(tmp_path):
    h = ScoreHistory(tmp_path, disabled=True)
    h.record("TEST", {"composite": 50.0})
    assert h.load("TEST") == []
    assert not (tmp_path / "TEST.json").exists()


def test_snapshot_from_analysis(patch_yfinance):
    analysis = asyncio.run(StockAnalyzer().analyze("TEST"))
    snap = snapshot_from_analysis(analysis)
    assert snap["price"] == 150.0
    assert 0 <= snap["composite"] <= 100
    assert snap["profile"] == "balanced"
    assert "value" in snap["lens_scores"]


# --- Score-history chart -----------------------------------------------------

def test_score_history_chart_needs_two_points():
    builder = ChartBuilder()
    one = [{"date": "2026-07-01", "composite": 50}]
    assert builder.create_score_history_chart(one, "TEST") is None
    two = one + [{"date": "2026-07-15", "composite": 62}]
    assert builder.create_score_history_chart(two, "TEST") is not None


def test_report_renders_score_history(tmp_path, patch_yfinance):
    h = ScoreHistory(tmp_path, disabled=False)
    # Pre-seed an older entry so today's run makes two points
    h.record("TEST", {"composite": 48.0})
    entries = h.load("TEST")
    entries[0]["date"] = "2026-01-02"
    import json
    (tmp_path / "TEST.json").write_text(json.dumps(entries))

    gen = ReportGenerator(history=h)
    out = tmp_path / "report.html"
    asyncio.run(gen.generate_report("TEST", str(out)))
    html = out.read_text(encoding="utf-8")
    assert 'id="score-history"' in html


# --- Screener ----------------------------------------------------------------

def test_build_row(patch_yfinance):
    analysis = asyncio.run(StockAnalyzer().analyze("TEST"))
    row = build_row("TEST", analysis, include_filings=False)
    assert row.symbol == "TEST"
    assert row.name == "Test Corp"
    assert 0 <= row.composite <= 100
    assert row.red_flag_count is None       # filings not requested


def test_build_row_with_filings(patch_yfinance, fake_edgar_client):
    analyzer = StockAnalyzer(filings_analyzer=FilingsAnalyzer(client=fake_edgar_client))
    analysis = asyncio.run(analyzer.analyze("TEST", include_filings=True))
    row = build_row("TEST", analysis, include_filings=True)
    assert row.red_flag_count >= 1          # fixture has going-concern + 8-K flags
    assert row.leverage_trend == "Rising"   # fixture debt series rises


def test_screener_ranks_and_dedupes(tmp_path, patch_yfinance):
    screener = Screener(history=ScoreHistory(tmp_path, disabled=False))
    rows = asyncio.run(screener.run(["TEST", "test", "AAA"]))
    ok = [r for r in rows if not r.error]
    assert len(ok) == 2                      # deduped TEST/test
    assert ok == sorted(ok, key=lambda r: r.composite, reverse=True)
    # History recorded for each analyzed symbol
    assert len(ScoreHistory(tmp_path, disabled=False).load("TEST")) == 1


def test_screener_isolates_failures(tmp_path, monkeypatch, patch_yfinance, fake_ticker):
    import yfinance

    def ticker_factory(symbol, *a, **k):
        if symbol.upper() == "BAD":
            raise RuntimeError("boom")
        return fake_ticker

    monkeypatch.setattr(yfinance, "Ticker", ticker_factory)
    screener = Screener(history=ScoreHistory(tmp_path, disabled=False))
    rows = asyncio.run(screener.run(["TEST", "BAD"]))
    assert [r.symbol for r in rows if r.error] == ["BAD"]
    assert [r.symbol for r in rows if not r.error] == ["TEST"]


# --- Screen report (HTML + CSV) ----------------------------------------------

def test_screen_report_writes_html_and_csv(tmp_path, patch_yfinance):
    gen = ScreenReportGenerator(
        screener=Screener(history=ScoreHistory(tmp_path, disabled=False)),
    )
    out = tmp_path / "screen.html"
    path = asyncio.run(gen.generate(["TEST", "ZZZZ"], str(out)))

    html = out.read_text(encoding="utf-8")
    assert "Universe Screen" in html
    assert "Test Corp" in html

    csv_path = out.with_suffix(".csv")
    assert csv_path.exists()
    with open(csv_path) as f:
        records = list(csv.DictReader(f))
    assert records[0]["symbol"] == "TEST"
    assert records[0]["rank"] == "1"
    assert str(path) == str(out)


def test_write_csv_filings_columns(tmp_path):
    rows = [ScreenRow(symbol="A", name="A Corp", composite=70,
                      lens_scores={"value": 60}, red_flag_count=2,
                      leverage_trend="Rising")]
    path = tmp_path / "s.csv"
    write_csv(rows, path, include_filings=True)
    with open(path) as f:
        records = list(csv.DictReader(f))
    assert records[0]["red_flags"] == "2"
    assert records[0]["leverage_trend"] == "Rising"
