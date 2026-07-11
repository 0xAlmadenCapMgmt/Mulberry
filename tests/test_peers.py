"""Integration tests for Phase 2: peers, multiples, forward context, profiles.

All offline via the patched-yfinance fixtures. Peers reuse the same fake ticker,
so every comparable metric ties — a clean, deterministic 50th-percentile result.
"""

import asyncio

import pytest

from mulberry.core.stock_analysis import StockAnalyzer
from mulberry.reports.generator import ReportGenerator


@pytest.fixture
def analyzer():
    return StockAnalyzer()


def test_multiples_and_forward_in_result(analyzer, patch_yfinance):
    result = asyncio.run(analyzer.analyze("TEST"))

    assert "multiples" in result
    assert result["multiples"].ev_sales > 0

    assert "forward" in result
    assert result["forward"].has_data is True
    assert result["forward"].forward_pe == pytest.approx(22.0)

    assert result["profile"] == "balanced"
    assert "peer_comparison" not in result   # none requested


def test_analyze_with_peers_ties_at_median(analyzer, patch_yfinance):
    result = asyncio.run(analyzer.analyze("TEST", peers=["PEERA", "PEERB"]))
    pc = result["peer_comparison"]

    assert pc is not None
    assert pc.peer_symbols == ["PEERA", "PEERB"]
    assert len(pc.results) > 0
    # Identical fake data across target and peers => every metric ties => 0.5
    for r in pc.results:
        assert r.percentile == pytest.approx(0.5)
    assert pc.overall_percentile == pytest.approx(0.5)


def test_peers_exclude_target_and_duplicates(analyzer, patch_yfinance):
    result = asyncio.run(analyzer.analyze("TEST", peers=["TEST", "PEERA", "PEERA"]))
    assert result["peer_comparison"].peer_symbols == ["PEERA"]


def test_profile_flows_through_pipeline(patch_yfinance):
    analyzer = StockAnalyzer(profile="deep_value")
    result = asyncio.run(analyzer.analyze("TEST"))
    assert result["profile"] == "deep_value"
    # Payer, so no dividend redistribution — value weight is the profile's 0.45
    assert result["frameworks"]["composite"].weights["value"] == pytest.approx(0.45)


def test_report_renders_phase2_sections(tmp_path, patch_yfinance):
    generator = ReportGenerator(profile="garp")
    out = tmp_path / "report.html"
    asyncio.run(generator.generate_report("TEST", str(out), peers=["PEERA", "PEERB"]))

    html = out.read_text(encoding="utf-8")
    assert "Peer-Relative Comparison" in html
    assert "Relative-Valuation Multiples" in html
    assert "Forward-Looking View" in html
    assert "Growth at a Reasonable Price" in html   # garp profile label
