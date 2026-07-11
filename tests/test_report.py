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
