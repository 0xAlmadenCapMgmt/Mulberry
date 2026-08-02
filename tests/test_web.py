"""Tests for the FastAPI web front end (offline via patched yfinance)."""

import pytest
from fastapi.testclient import TestClient

from mulberry.ai.agent import AgentReply
from mulberry.web.app import create_app
from mulberry.utils.config import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    """App whose output dir is a fresh tmp dir (no writes into the project)."""
    monkeypatch.setattr(config, "output_dir", tmp_path)
    return TestClient(create_app())


class _FakeAgent:
    """Duck-typed agent: echoes the question, no network."""

    def __init__(self, symbol):
        self.symbol = symbol

    def ask(self, question, history=None):
        history = list(history or [])
        answer = f"Answer about {self.symbol}: {question}"
        new_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        return AgentReply(answer=answer, history=new_history,
                          tools_used=["get_metric"], model="fake")


@pytest.fixture
def ask_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "output_dir", tmp_path)
    app = create_app(agent_factory=lambda symbol, profile: _FakeAgent(symbol))
    return TestClient(app)


# --- Static pages ------------------------------------------------------------

def test_home_page(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Analyze a stock" in r.text
    assert "balanced" in r.text  # profile dropdown populated


def test_screen_form(client):
    r = client.get("/screen")
    assert r.status_code == 200
    assert "Screen a universe" in r.text


def test_ask_page_renders_and_prefills_symbol(client):
    r = client.get("/ask?symbol=aapl")
    assert r.status_code == 200
    assert "Ask about a stock" in r.text
    assert 'value="AAPL"' in r.text


def test_ask_api_answers(ask_client):
    r = ask_client.post("/ask", json={"symbol": "AAPL", "question": "why?"})
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "Answer about AAPL: why?"
    assert data["symbol"] == "AAPL"
    assert data["tools_used"] == ["get_metric"]
    # History threads user + assistant turns for the next request.
    assert data["history"][-2:] == [
        {"role": "user", "content": "why?"},
        {"role": "assistant", "content": "Answer about AAPL: why?"},
    ]


def test_ask_api_threads_history(ask_client):
    prior = [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
    ]
    r = ask_client.post("/ask", json={"symbol": "AAPL", "question": "q2", "history": prior})
    assert r.status_code == 200
    assert r.json()["history"][:2] == prior


def test_ask_api_rejects_bad_input(ask_client):
    assert ask_client.post("/ask", json={"symbol": "!!!", "question": "hi"}).status_code == 400
    assert ask_client.post("/ask", json={"symbol": "AAPL", "question": ""}).status_code == 400


def test_glossary_page(client):
    r = client.get("/glossary")
    assert r.status_code == 200
    assert "Glossary" in r.text
    # A representative term, an alias, and a formula are all rendered.
    assert "Net Current Asset Value" in r.text
    assert "Sharpe Ratio" in r.text
    assert 'id="glossary-margin-of-safety"' in r.text


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# --- Analyze flow ------------------------------------------------------------

def test_analyze_generates_and_serves(client, patch_yfinance):
    r = client.post(
        "/analyze",
        data={"symbol": "TEST", "profile": "balanced"},  # filings/thesis off
        follow_redirects=False,
    )
    assert r.status_code == 303
    location = r.headers["location"]
    assert location.startswith("/reports/analysis_TEST_")

    report = client.get(location)
    assert report.status_code == 200
    assert "Test Corp" in report.text
    assert "Multi-Framework Scorecard" in report.text


def test_analyze_invalid_ticker(client):
    r = client.post("/analyze", data={"symbol": "!!!"}, follow_redirects=False)
    assert r.status_code == 400
    assert "went wrong" in r.text.lower() or "invalid" in r.text.lower()


def test_analyze_bad_profile(client, patch_yfinance):
    r = client.post("/analyze", data={"symbol": "TEST", "profile": "nonsense"},
                    follow_redirects=False)
    assert r.status_code == 400


# --- Screen flow -------------------------------------------------------------

def test_screen_runs_and_serves(client, patch_yfinance):
    r = client.post("/screen", data={"symbols": "TEST AAA", "profile": "balanced"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/reports/screen_")

    report = client.get(r.headers["location"])
    assert report.status_code == 200
    assert "Universe Screen" in report.text


def test_screen_empty(client):
    r = client.post("/screen", data={"symbols": "   "}, follow_redirects=False)
    assert r.status_code == 400


# --- History + report serving ------------------------------------------------

def test_reports_history_lists_generated(client, patch_yfinance):
    client.post("/analyze", data={"symbol": "TEST", "profile": "balanced"})
    r = client.get("/reports")
    assert r.status_code == 200
    assert "TEST" in r.text


def test_report_serving_rejects_traversal(client):
    # unknown file, bad extension, and traversal attempts all 404
    assert client.get("/reports/missing.html").status_code == 404
    assert client.get("/reports/evil.txt").status_code == 404
    assert client.get("/reports/..%2f..%2fetc%2fpasswd").status_code == 404


def test_report_serving_rejects_absolute_and_subpath(client, tmp_path):
    # A real file outside output_dir must not be served by name games
    secret = tmp_path.parent / "secret.html"
    secret.write_text("top secret")
    assert client.get(f"/reports/{secret.name}").status_code == 404
