"""Tests for the SEC EDGAR client (HTTP layer monkeypatched — no network)."""

import pytest

from mulberry.api.sec_edgar import SECEdgarClient


@pytest.fixture
def client():
    return SECEdgarClient(user_agent="Tester test@example.com")


def test_resolve_cik_zero_pads(client, monkeypatch):
    monkeypatch.setattr(client, "_fetch_json", lambda url: {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft"},
    })
    assert client.resolve_cik("aapl") == "0000320193"
    assert client.resolve_cik("MSFT") == "0000789019"
    assert client.resolve_cik("ZZZZ") is None


def test_resolve_cik_graceful_on_error(client, monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(client, "_fetch_json", boom)
    assert client.resolve_cik("AAPL") is None


def test_get_submissions_passthrough_and_graceful(client, monkeypatch):
    monkeypatch.setattr(client, "_fetch_json", lambda url: {"name": "Apple"})
    assert client.get_submissions("0000320193") == {"name": "Apple"}

    def boom(url):
        raise RuntimeError("500")
    monkeypatch.setattr(client, "_fetch_json", boom)
    assert client.get_submissions("0000320193") is None


def test_get_company_facts_graceful(client, monkeypatch):
    def boom(url):
        raise RuntimeError("timeout")
    monkeypatch.setattr(client, "_fetch_json", boom)
    assert client.get_company_facts("0000320193") is None


def test_get_filing_document_builds_archive_url(client, monkeypatch):
    captured = {}

    def fake_text(url):
        captured["url"] = url
        return "<html>doc</html>"

    monkeypatch.setattr(client, "_fetch_text", fake_text)
    out = client.get_filing_document("0000320193", "0000320193-24-000005", "aapl-10k.htm")

    assert out == "<html>doc</html>"
    # CIK int (no zero-pad), accession stripped of dashes, document name
    assert "edgar/data/320193/000032019324000005/aapl-10k.htm" in captured["url"]


def test_placeholder_user_agent_detected():
    default = SECEdgarClient(user_agent="FinancialAnalysis contact@example.com")
    assert default.using_placeholder_user_agent is True
    real = SECEdgarClient(user_agent="Almaden research@almaden.com")
    assert real.using_placeholder_user_agent is False
