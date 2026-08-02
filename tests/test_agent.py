"""Tests for the conversational analysis agent (offline — fake client/analyzer)."""

import asyncio
from types import SimpleNamespace

import pytest

from mulberry.ai import agent as agent_mod
from mulberry.ai.agent import AnalysisAgent, _lens_detail, _metric_snapshot
from mulberry.core.stock_analysis import StockAnalyzer


@pytest.fixture
def analysis(patch_yfinance):
    """A real computed analysis from the patched-yfinance pipeline."""
    return asyncio.run(StockAnalyzer().analyze("TEST"))


# --- Fakes -------------------------------------------------------------------

def _text_block(text):
    return SimpleNamespace(type="text", text=text)


def _tool_block(name, tool_input, id="tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=id)


class ScriptedClient:
    """Returns a queued list of responses across successive create() calls."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kwargs):
        self.requests.append(kwargs)
        resp = self._responses.pop(0)
        return SimpleNamespace(model=kwargs.get("model", ""), **resp)


class FakeAnalyzer:
    """Stands in for StockAnalyzer.analyze for the analyze_ticker tool."""

    def __init__(self, result):
        self._result = result

    async def analyze(self, symbol, **kwargs):
        return dict(self._result, symbol=symbol)


# --- Availability ------------------------------------------------------------

def test_agent_unavailable_without_key(monkeypatch, analysis):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ag = AnalysisAgent(analysis=analysis, api_key="")
    assert ag.available is False
    reply = ag.ask("why is the score what it is?")
    assert "ANTHROPIC_API_KEY" in reply.answer
    # A failed/unavailable turn still returns cleanly with no history growth.
    assert reply.history == []


# --- Grounding helpers (pure) -----------------------------------------------

def test_metric_snapshot_has_headline_numbers(analysis):
    snap = _metric_snapshot(analysis)
    assert "composite score" in snap
    assert 0 <= snap["composite score"] <= 100
    assert "margin of safety" in snap
    assert snap["recommendation"]


def test_get_metric_matches_loose_names(analysis):
    ag = AnalysisAgent(analysis=analysis, client=object())
    assert ag._tool_get_metric("composite score")["value"] == pytest.approx(
        analysis["frameworks"]["composite"].overall_score
    )
    # Loose / aliased name resolves via substring.
    assert "value" in ag._tool_get_metric("P/E")


def test_get_metric_unknown_lists_available(analysis):
    ag = AnalysisAgent(analysis=analysis, client=object())
    out = ag._tool_get_metric("frobnication index")
    assert "error" in out
    assert "composite score" in out["available_metrics"]


def test_lens_detail_variants(analysis):
    quality = _lens_detail(analysis, "quality")
    assert quality["score"] is not None
    assert isinstance(quality["checks"], dict) and quality["checks"]

    composite = _lens_detail(analysis, "composite")
    assert set(["value", "quality", "growth"]).issubset(composite["lenses"])

    value = _lens_detail(analysis, "value")
    assert "graham_number" in value["methods"]

    bad = _lens_detail(analysis, "nonsense")
    assert "error" in bad and "available" in bad


def test_define_term_tool(analysis):
    ag = AnalysisAgent(analysis=analysis, client=object())
    out = ag._tool_define("NCAV")
    assert out["term"].startswith("Net Current Asset Value")
    assert out["definition"]
    assert "error" in ag._tool_define("not-a-real-term")


# --- Tool loop ---------------------------------------------------------------

def test_ask_runs_tool_loop_then_answers(analysis):
    client = ScriptedClient([
        {"stop_reason": "tool_use",
         "content": [_tool_block("get_metric", {"name": "composite score"})]},
        {"stop_reason": "end_turn",
         "content": [_text_block("The composite is a weighted blend of the five lenses.")]},
    ])
    ag = AnalysisAgent(analysis=analysis, client=client)
    reply = ag.ask("why is the composite what it is?")

    assert "weighted blend" in reply.answer
    assert reply.tools_used == ["get_metric"]
    # Two model calls: initial + after tool result.
    assert len(client.requests) == 2
    assert client.requests[0]["tools"], "tools must be passed to the model"
    # History threads the user turn and the final answer only (not tool exchanges).
    assert reply.history[-2] == {"role": "user", "content": "why is the composite what it is?"}
    assert reply.history[-1]["role"] == "assistant"


def test_ask_grounds_system_prompt_in_primary_analysis(analysis):
    client = ScriptedClient([
        {"stop_reason": "end_turn", "content": [_text_block("ok")]},
    ])
    ag = AnalysisAgent(analysis=analysis, client=client)
    ag.ask("hi")
    system = client.requests[0]["system"]
    assert "Primary analysis under discussion" in system
    assert "TEST" in system
    assert "not personalized investment advice" in system.lower() or "not a licensed advisor" in system.lower()


def test_ask_handles_refusal(analysis):
    client = ScriptedClient([{"stop_reason": "refusal", "content": []}])
    ag = AnalysisAgent(analysis=analysis, client=client)
    reply = ag.ask("do something disallowed")
    assert "can't help" in reply.answer.lower()


def test_ask_survives_client_error(analysis):
    class Exploding:
        @property
        def messages(self):
            raise RuntimeError("boom")
    ag = AnalysisAgent(analysis=analysis, client=Exploding())
    reply = ag.ask("hello")
    assert "error" in reply.answer.lower()


def test_ask_multi_turn_threads_prior_history(analysis):
    client = ScriptedClient([
        {"stop_reason": "end_turn", "content": [_text_block("first answer")]},
        {"stop_reason": "end_turn", "content": [_text_block("second answer")]},
    ])
    ag = AnalysisAgent(analysis=analysis, client=client)
    r1 = ag.ask("q1")
    r2 = ag.ask("q2", history=r1.history)
    # Second request carries the full prior conversation plus the new question.
    msgs = client.requests[1]["messages"]
    contents = [m["content"] for m in msgs]
    assert contents == ["q1", "first answer", "q2"]
    assert r2.answer == "second answer"


# --- analyze_ticker tool -----------------------------------------------------

def test_analyze_ticker_tool_uses_injected_analyzer(analysis):
    other = {  # minimal but valid analysis shape for build_payload
        "company_info": {"name": "Microsoft"}, "current_price": 400,
        "valuation": {}, "metrics": {"pe_ratio": 30},
        "frameworks": {"composite": analysis["frameworks"]["composite"]},
    }
    ag = AnalysisAgent(analysis=analysis, client=object(),
                       analyzer=FakeAnalyzer(other))
    out = ag._tool_analyze_ticker("MSFT")
    assert out["symbol"] == "MSFT"
    assert out["payload"]["symbol"] == "MSFT"
    assert out["payload"]["company"] == "Microsoft"


def test_analyze_ticker_rejects_bad_symbol(analysis):
    ag = AnalysisAgent(analysis=analysis, client=object(),
                       analyzer=FakeAnalyzer({}))
    assert "error" in ag._tool_analyze_ticker("!!!")
