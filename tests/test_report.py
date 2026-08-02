"""Smoke test: the HTML report renders end-to-end from patched data."""

import asyncio

from mulberry.reports.generator import ReportGenerator


def test_generate_report_writes_html(tmp_path, patch_yfinance):
    generator = ReportGenerator()
    out = tmp_path / "report.html"

    path = asyncio.run(generator.generate_report("TEST", str(out)))

    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "TEST" in html
    assert "Test Corp" in html
    # The report should embed at least one Plotly chart div
    assert "plotly" in html.lower()
    assert str(path) == str(out)


def test_report_includes_glossary_section_and_tooltips(tmp_path, patch_yfinance):
    generator = ReportGenerator()
    out = tmp_path / "report.html"
    asyncio.run(generator.generate_report("TEST", str(out)))
    html = out.read_text(encoding="utf-8")

    # Dedicated glossary section with anchored terms.
    assert 'id="glossary"' in html
    assert "Glossary &amp; Formulas" in html
    assert 'id="glossary-margin-of-safety"' in html
    assert "√(22.5 × EPS × Book Value per Share)" in html  # a formula rendered

    # Inline hover tooltips wired into the body (dotted-term spans).
    assert 'class="gloss"' in html
    assert 'data-tip="' in html

