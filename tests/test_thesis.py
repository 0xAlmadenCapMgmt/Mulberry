"""Tests for the AI thesis layer (offline — fake Anthropic client)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from mulberry.ai.thesis import ThesisGenerator, ThesisResult, build_payload
from mulberry.core.stock_analysis import StockAnalyzer
from mulberry.core.filings import FilingsAnalyzer
from mulberry.reports.generator import ReportGenerator


THESIS_JSON = {
    "thesis": "A quality compounder trading at a full price.",
    "bull_case": "Margins keep expanding and buybacks continue.",
    "bear_case": "Multiple compression as growth slows.",
    "risks": ["Valuation risk", "Regulatory scrutiny", "Concentration in one product"],
}


class FakeAnthropicClient:
    """Mimics the slice of anthropic.Anthropic the generator uses."""

    def __init__(self, response_text=None, stop_reason="end_turn"):
        self._text = response_text if response_text is not None else json.dumps(THESIS_JSON)
        self._stop_reason = stop_reason
        self.last_request = None
        self.messages = self

    def create(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(
            stop_reason=self._stop_reason,
            model=kwargs.get("model", ""),
            content=[SimpleNamespace(type="text", text=self._text)],
        )


# --- Availability / graceful degradation ------------------------------------

def test_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gen = ThesisGenerator(api_key="")
    assert gen.available is False
    assert gen.generate({"symbol": "TEST"}) is None


def test_generate_returns_none_on_bad_json():
    gen = ThesisGenerator(client=FakeAnthropicClient(response_text="not json"))
    assert gen.generate({"symbol": "TEST"}) is None


def test_generate_returns_none_on_refusal():
    gen = ThesisGenerator(client=FakeAnthropicClient(stop_reason="refusal"))
    assert gen.generate({"symbol": "TEST"}) is None


def test_generate_returns_none_on_client_error():
    class Exploding:
        @property
        def messages(self):
            raise RuntimeError("network down")
    gen = ThesisGenerator(client=Exploding())
    assert gen.generate({"symbol": "TEST"}) is None


# --- Happy path --------------------------------------------------------------

def test_generate_parses_structured_output():
    fake = FakeAnthropicClient()
    gen = ThesisGenerator(client=fake, model="claude-opus-4-8")
    result = gen.generate({"symbol": "TEST"})

    assert isinstance(result, ThesisResult)
    assert result.thesis == THESIS_JSON["thesis"]
    assert result.bull_case == THESIS_JSON["bull_case"]
    assert len(result.risks) == 3

    # Request shape: structured output schema + adaptive thinking + system prompt
    req = fake.last_request
    assert req["model"] == "claude-opus-4-8"
    assert req["thinking"] == {"type": "adaptive"}
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "not personalized investment advice" in req["system"] or "not investment advice" in req["system"]


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("THESIS_MODEL", "claude-sonnet-5")
    gen = ThesisGenerator(api_key="sk-test", client=FakeAnthropicClient())
    assert gen.model == "claude-sonnet-5"


# --- Payload construction (pure) ---------------------------------------------

def test_build_payload_from_pipeline(patch_yfinance, fake_edgar_client):
    analyzer = StockAnalyzer(filings_analyzer=FilingsAnalyzer(client=fake_edgar_client))
    analysis = asyncio.run(analyzer.analyze("TEST", include_filings=True))
    payload = build_payload(analysis)

    assert payload["symbol"] == "TEST"
    assert payload["company"] == "Test Corp"
    assert 0 <= payload["composite"]["overall_score"] <= 100
    assert "lens_verdicts" in payload["composite"]
    assert payload["data_confidence"]["level"] in ("High", "Medium", "Low")
    # Filing context flows through for synthesis
    sec = payload["sec_filings"]
    assert any(f["label"] == "Going concern" for f in sec["red_flags"])
    assert any(t["metric"] == "Long-term debt" and t["favorable"] is False
               for t in sec["trends"])
    assert any(s["section"] == "Risk Factors" for s in sec["filing_excerpts"])
    # Payload must be JSON-serializable as sent to the API
    json.dumps(payload, default=str)


def test_build_payload_minimal_analysis():
    payload = build_payload({"symbol": "X", "current_price": 10})
    assert payload["symbol"] == "X"
    assert "composite" not in payload
    assert "sec_filings" not in payload


# --- Report integration ------------------------------------------------------

def test_report_renders_thesis_section(tmp_path, patch_yfinance):
    gen = ReportGenerator(thesis_generator=ThesisGenerator(client=FakeAnthropicClient()))
    out = tmp_path / "report.html"
    asyncio.run(gen.generate_report("TEST", str(out), include_thesis=True))

    html = out.read_text(encoding="utf-8")
    assert "Investment Thesis" in html
    assert "AI-generated" in html
    assert THESIS_JSON["thesis"] in html
    assert "Bull Case" in html and "Bear Case" in html


def test_report_omits_thesis_without_key(tmp_path, patch_yfinance, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    gen = ReportGenerator(thesis_generator=ThesisGenerator(api_key=""))
    out = tmp_path / "report.html"
    asyncio.run(gen.generate_report("TEST", str(out), include_thesis=True))

    html = out.read_text(encoding="utf-8")
    assert 'id="thesis"' not in html         # section cleanly omitted
    assert "Multi-Framework Scorecard" in html  # rest of report intact
