"""Tests for the SEC filings engine (offline, fake EDGAR client)."""

import asyncio

import pytest

from mulberry.core.filings import (
    html_to_text,
    extract_annual_series,
    build_trend,
    extract_section,
    text_red_flags,
    FilingsAnalyzer,
)
from mulberry.core.stock_analysis import StockAnalyzer
from mulberry.reports.generator import ReportGenerator


# --- Pure helpers ----------------------------------------------------------

def test_html_to_text_strips_tags_and_scripts():
    assert html_to_text("<p>Hello&nbsp;<b>world</b></p>") == "Hello world"
    assert html_to_text("<style>a{}</style><script>x=1</script><p>Body</p>").strip() == "Body"
    assert html_to_text("") == ""


def test_extract_annual_series_filters_and_sorts():
    facts = {"facts": {"us-gaap": {"Liabilities": {"units": {"USD": [
        {"end": "2022-09-30", "val": 270, "form": "10-K", "fp": "FY"},
        {"end": "2023-09-30", "val": 280, "form": "10-K", "fp": "FY"},
        {"end": "2021-09-30", "val": 250, "form": "10-K", "fp": "FY"},
        {"end": "2023-06-30", "val": 275, "form": "10-Q", "fp": "Q3"},   # non-annual
    ]}}}}}
    series = extract_annual_series(facts, ["Liabilities"], "USD")
    assert series == [("2021-09-30", 250.0), ("2022-09-30", 270.0), ("2023-09-30", 280.0)]


def test_extract_annual_series_tag_fallback():
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"end": "2023-09-30", "val": 400, "form": "10-K", "fp": "FY"},
        {"end": "2022-09-30", "val": 380, "form": "10-K", "fp": "FY"},
    ]}}}}}
    series = extract_annual_series(
        facts, ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"], "USD"
    )
    assert len(series) == 2


def test_build_trend_direction_and_change():
    t = build_trend("Cash", "USD", True, [("2021", 60), ("2024", 50)])
    assert t.direction == "Falling"
    assert t.change_pct == pytest.approx(-1 / 6, abs=0.01)
    # Rising example
    up = build_trend("Debt", "USD", False, [("2021", 100), ("2024", 130)])
    assert up.direction == "Rising"
    # Too short
    assert build_trend("x", "USD", True, [("2021", 100)]) is None


def test_extract_section_uses_last_occurrence():
    text = (
        "Table of Contents Management's Discussion and Analysis page 30 . "
        "Business overview here. Management's Discussion and Analysis " + "Z" * 200
    )
    section = extract_section(text, "Management's Discussion and Analysis")
    assert section is not None
    assert section.startswith("Z")


def test_extract_section_missing_returns_none():
    assert extract_section("no such heading here", "Risk Factors") is None


# --- Red-flag precision (the part most prone to false positives) ------------

def test_going_concern_flag_fires_on_real_trigger():
    text = ("Certain conditions raise substantial doubt about the Company's "
            "ability to continue as a going concern.")
    flags = text_red_flags(text)
    assert len(flags) == 1
    assert flags[0].severity == "high"


def test_going_concern_not_flagged_when_negated():
    # The ubiquitous healthy-filing boilerplate must NOT flag.
    text = ("Management concluded there is no substantial doubt about the "
            "Company's ability to continue as a going concern.")
    assert text_red_flags(text) == []


def test_material_weakness_boilerplate_not_flagged():
    # "no material weakness" and the SOX definition must not produce a flag.
    text = ("A material weakness is a deficiency in internal control. Based on "
            "our evaluation, no material weakness was identified.")
    assert text_red_flags(text) == []


# --- FilingsAnalyzer end-to-end (fake client) ------------------------------

def test_analyze_full(fake_edgar_client):
    assessment = FilingsAnalyzer(client=fake_edgar_client).analyze("AAPL")

    assert assessment is not None
    assert assessment.entity_name == "Apple Inc."
    assert assessment.latest_10k is not None
    assert assessment.latest_10q is not None
    assert assessment.days_since_last_periodic == 30      # from the 10-Q
    assert assessment.recent_8k_count == 2
    assert len(assessment.trends) == 8

    labels = {f.label for f in assessment.red_flags}
    severities = {f.severity for f in assessment.red_flags}
    # going concern (text), 8-K items (4.02 high, 5.02 info), derived leverage (medium)
    assert "high" in severities and "medium" in severities and "info" in severities
    assert "Going concern" in labels
    assert any("Leverage" in l for l in labels)
    assert any("8-K Item 4.02" == l for l in labels)
    # "no material weakness" boilerplate must not have produced a flag
    assert not any("weakness" in l.lower() for l in labels)

    titles = {s.title for s in assessment.sections}
    assert "Management's Discussion & Analysis" in titles
    assert "Risk Factors" in titles


def test_analyze_unresolved_ticker_returns_none():
    class NoCik:
        def resolve_cik(self, ticker):
            return None
    assert FilingsAnalyzer(client=NoCik()).analyze("ZZZZ") is None


def test_analyze_no_data_returns_none():
    class Empty:
        def resolve_cik(self, ticker):
            return "0000000001"
        def get_submissions(self, cik):
            return None
        def get_company_facts(self, cik):
            return None
    assert FilingsAnalyzer(client=Empty()).analyze("X") is None


def test_debt_trend_flagged_unfavorable(fake_edgar_client):
    assessment = FilingsAnalyzer(client=fake_edgar_client).analyze("AAPL")
    debt = next(t for t in assessment.trends if t.label == "Long-term debt")
    assert debt.direction == "Rising"
    assert debt.higher_is_better is False   # rising debt is unfavorable


# --- Pipeline & report integration -----------------------------------------

def test_pipeline_attaches_filings(patch_yfinance, fake_edgar_client):
    analyzer = StockAnalyzer(filings_analyzer=FilingsAnalyzer(client=fake_edgar_client))
    result = asyncio.run(analyzer.analyze("TEST", include_filings=True))

    assert result["filings"] is not None
    assert any("SEC filings" in note for note in result["data_confidence"].notes)


def test_pipeline_filings_off_by_default(patch_yfinance):
    result = asyncio.run(StockAnalyzer().analyze("TEST"))
    assert "filings" not in result


def test_report_renders_filings_section(tmp_path, patch_yfinance, fake_edgar_client):
    analyzer = StockAnalyzer(filings_analyzer=FilingsAnalyzer(client=fake_edgar_client))
    generator = ReportGenerator(analyzer=analyzer)
    out = tmp_path / "report.html"
    asyncio.run(generator.generate_report("TEST", str(out), include_filings=True))

    html = out.read_text(encoding="utf-8")
    assert "SEC Filings" in html
    assert "Multi-Year Trends" in html
    assert "Risk Factors" in html
