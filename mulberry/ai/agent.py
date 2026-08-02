"""
Conversational analysis agent.

Lets a user interrogate a Mulberry report in natural language — "why is the
composite only 60?", "how does the DCF get to that number?", "what does NCAV
mean?", "how does it compare to MSFT?". It's a Claude tool-use loop grounded in
the **already-computed** analysis: the model may look up a computed metric, drill
into a lens's per-criterion checks, define a glossary term, or run a fresh
analysis on another ticker — but it never invents figures and never contradicts
the computed scores.

Guardrails mirror the thesis layer: educational research context only, never
personalized buy/sell advice. Generation is optional — without an Anthropic API
key the agent is simply unavailable and callers say so. Fully offline-testable
via an injected client (and an injected analyzer for the ``analyze_ticker`` tool).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core import glossary
from ..utils.logger import get_logger
from .thesis import build_payload

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are Mulberry's analysis assistant. A user is reading a computed, "
    "multi-framework stock analysis and wants to understand it more deeply. "
    "You are given the primary company's computed analysis as JSON, and tools to "
    "look up specific metrics, drill into a framework lens's checks, define a "
    "glossary term, or analyze another ticker for comparison.\n\n"
    "Rules:\n"
    "- Ground every claim in the provided data or a tool result. Never invent "
    "figures, and never contradict Mulberry's computed scores or recommendation.\n"
    "- Use tools when a question needs a specific number, a lens breakdown, a "
    "definition, or another company — don't guess.\n"
    "- Be concise and concrete. Explain the 'why' behind a score using the "
    "underlying checks.\n"
    "- This is educational research context, not personalized investment advice. "
    "Never tell the user to buy, sell, or hold, and if asked for a personal "
    "recommendation, explain that Mulberry is educational and not a licensed advisor."
)

# Tool schemas exposed to the model.
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_metric",
        "description": (
            "Look up a single computed metric or score for the PRIMARY company by "
            "name, e.g. 'composite score', 'ROE', 'margin of safety', 'P/E', "
            "'DCF value', 'quality score', 'dividend yield'. Returns the value "
            "Mulberry already computed (no recomputation)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Metric or score name"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_lens_detail",
        "description": (
            "Get the per-criterion breakdown for one analysis lens of the PRIMARY "
            "company. Returns each check's target, actual value, and pass/fail so "
            "you can explain WHY a lens scored the way it did."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lens": {
                    "type": "string",
                    "enum": ["value", "quality", "growth", "dividend", "momentum", "composite"],
                }
            },
            "required": ["lens"],
        },
    },
    {
        "name": "define_term",
        "description": (
            "Define a Mulberry glossary term or formula in plain language, e.g. "
            "'NCAV', 'Sharpe ratio', 'PEG', 'margin of safety', 'EV/EBITDA'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"}},
            "required": ["term"],
        },
    },
    {
        "name": "analyze_ticker",
        "description": (
            "Run Mulberry's full analysis on ANOTHER ticker (not the primary one) "
            "and return its computed summary, for comparison. This fetches live "
            "market data, so use it only when the user asks to compare or bring in "
            "another company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
        },
    },
]


@dataclass
class AgentReply:
    """One turn's result."""
    answer: str
    history: List[Dict[str, str]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    model: str = ""


class AnalysisAgent:
    """Grounded, tool-using Q&A over a computed analysis.

    Degrades gracefully: if no API key is configured, :attr:`available` is False
    and callers should surface that rather than calling :meth:`ask`.
    """

    def __init__(
        self,
        analysis: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client=None,
        analyzer=None,
        max_tool_iterations: int = 6,
    ):
        self.analysis = analysis
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("AGENT_MODEL", "") or DEFAULT_MODEL
        self._client = client  # injectable for tests
        self._analyzer = analyzer  # StockAnalyzer-like; injectable for tests
        self.max_tool_iterations = max_tool_iterations

    @property
    def available(self) -> bool:
        return self._client is not None or bool(self.api_key)

    @property
    def symbol(self) -> str:
        return (self.analysis or {}).get("symbol", "") if self.analysis else ""

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _get_analyzer(self):
        if self._analyzer is None:
            from ..core.stock_analysis import StockAnalyzer
            profile = (self.analysis or {}).get("profile", "balanced")
            self._analyzer = StockAnalyzer(profile=profile)
        return self._analyzer

    # ------------------------------------------------------------------
    # Conversation
    # ------------------------------------------------------------------

    def ask(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> AgentReply:
        """Answer ``question`` grounded in the analysis, running the tool loop.

        ``history`` is a list of prior ``{"role", "content"}`` text turns; the
        returned reply carries the updated history (question + answer appended)
        so a caller can thread a multi-turn conversation. Tool exchanges are
        internal to a single turn and are not persisted in the returned history.
        """
        history = list(history or [])
        if not self.available:
            answer = (
                "The analysis assistant needs an ANTHROPIC_API_KEY to run. "
                "Set one to ask questions about this report."
            )
            return AgentReply(answer=answer, history=history, model=self.model)

        try:
            import anthropic
        except ImportError:
            answer = "The analysis assistant needs the `anthropic` package installed."
            return AgentReply(answer=answer, history=history, model=self.model)

        # Build the message list: prior text turns + this question.
        messages: List[Dict[str, Any]] = [
            {"role": t["role"], "content": t["content"]} for t in history
        ]
        messages.append({"role": "user", "content": question})

        system = SYSTEM_PROMPT
        if self.analysis is not None:
            system += (
                "\n\nPrimary analysis under discussion (JSON):\n"
                + json.dumps(build_payload(self.analysis), indent=2, default=str)
            )

        client = self._get_client()
        tools_used: List[str] = []

        try:
            response = client.messages.create(
                model=self.model, max_tokens=4000, system=system,
                tools=TOOLS, messages=messages,
            )
            iterations = 0
            while (
                getattr(response, "stop_reason", None) == "tool_use"
                and iterations < self.max_tool_iterations
            ):
                iterations += 1
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    tools_used.append(block.name)
                    result = self._run_tool(block.name, dict(block.input or {}))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                messages.append({"role": "user", "content": tool_results})
                response = client.messages.create(
                    model=self.model, max_tokens=4000, system=system,
                    tools=TOOLS, messages=messages,
                )

            if getattr(response, "stop_reason", None) == "refusal":
                answer = (
                    "I can't help with that request. I can explain the metrics, "
                    "scores, and methodology in this report as educational context."
                )
            else:
                answer = "".join(
                    b.text for b in response.content if getattr(b, "type", None) == "text"
                ).strip() or "(no answer)"
        except anthropic.AuthenticationError:
            answer = "The configured Anthropic API key was rejected."
        except Exception as e:  # graceful degradation — never crash the caller
            logger.warning(f"Agent turn failed: {e}")
            answer = f"Sorry — the assistant hit an error answering that ({e})."

        new_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        return AgentReply(
            answer=answer, history=new_history,
            tools_used=tools_used, model=self.model,
        )

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def _run_tool(self, name: str, tool_input: Dict[str, Any]) -> str:
        """Dispatch a tool call; always returns a JSON string (never raises)."""
        try:
            if name == "get_metric":
                return json.dumps(self._tool_get_metric(tool_input.get("name", "")))
            if name == "get_lens_detail":
                return json.dumps(self._tool_lens_detail(tool_input.get("lens", "")), default=str)
            if name == "define_term":
                return json.dumps(self._tool_define(tool_input.get("term", "")))
            if name == "analyze_ticker":
                return json.dumps(self._tool_analyze_ticker(tool_input.get("symbol", "")), default=str)
            return json.dumps({"error": f"unknown tool {name!r}"})
        except Exception as e:  # never let a tool crash the loop
            logger.warning(f"Tool {name} failed: {e}")
            return json.dumps({"error": str(e)})

    def _tool_get_metric(self, name: str) -> Dict[str, Any]:
        snap = _metric_snapshot(self.analysis)
        key = glossary._norm(name)
        if key in snap:
            return {"name": name, "value": snap[key]}
        # substring match
        hits = {k: v for k, v in snap.items() if key and (key in k or k in key)}
        if len(hits) == 1:
            k, v = next(iter(hits.items()))
            return {"name": k, "value": v}
        return {
            "error": f"no single metric matched {name!r}",
            "available_metrics": sorted(snap.keys()),
        }

    def _tool_lens_detail(self, lens: str) -> Dict[str, Any]:
        return _lens_detail(self.analysis, lens)

    def _tool_define(self, term: str) -> Dict[str, Any]:
        entry = glossary.lookup(term)
        if entry is None:
            return {"error": f"no glossary term matched {term!r}"}
        return {
            "term": entry.term,
            "definition": entry.definition,
            "formula": entry.formula or None,
            "category": entry.category,
        }

    def _tool_analyze_ticker(self, symbol: str) -> Dict[str, Any]:
        from ..utils.validators import validate_ticker, normalize_ticker
        ok, err = validate_ticker(symbol)
        if not ok:
            return {"error": f"invalid ticker {symbol!r}: {err}"}
        symbol = normalize_ticker(symbol)
        if symbol == self.symbol:
            return {"note": "that is the primary company already under discussion",
                    "payload": build_payload(self.analysis)}
        try:
            analyzer = self._get_analyzer()
            analysis = asyncio.run(analyzer.analyze(symbol))
        except Exception as e:
            return {"error": f"could not analyze {symbol}: {e}"}
        return {"symbol": symbol, "payload": build_payload(analysis)}


# ---------------------------------------------------------------------------
# Grounding helpers (pure — unit-tested directly)
# ---------------------------------------------------------------------------

def _metric_snapshot(analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """A flat, normalized-key map of the report's headline numbers.

    Keys are glossary-normalized (lowercase, alnum) so ``get_metric`` can match
    loose natural-language names like "composite score" or "P/E".
    """
    snap: Dict[str, Any] = {}
    if not analysis:
        return snap

    def put(label: str, value: Any) -> None:
        if value is not None:
            snap[glossary._norm(label)] = value

    put("current price", analysis.get("current_price"))
    put("recommendation", analysis.get("recommendation"))

    valuation = analysis.get("valuation", {})
    put("avg intrinsic value", valuation.get("avg_intrinsic_value"))
    put("graham number", valuation.get("graham_number"))
    put("ncav per share", valuation.get("ncav_per_share"))
    put("normalized value", valuation.get("normalized_value"))
    margins = valuation.get("margins_of_safety", {})
    put("margin of safety", margins.get("average"))
    put("graham margin of safety", margins.get("graham"))
    put("ncav margin of safety", margins.get("ncav"))

    frameworks = analysis.get("frameworks", {})
    composite = frameworks.get("composite")
    if composite is not None:
        put("composite score", composite.overall_score)
        put("profile", composite.profile)
        for lens, score in composite.lens_scores.items():
            put(f"{lens} score", score)
    for lens in ("quality", "growth", "dividend"):
        obj = frameworks.get(lens)
        if obj is not None:
            put(f"{lens} score", obj.score)
            put(f"{lens} rating", obj.rating)
    momentum = frameworks.get("momentum")
    if momentum is not None:
        put("momentum score", momentum.score)
        put("momentum signal", momentum.signal)
        put("volatility", getattr(momentum, "volatility_annual", None))
        put("max drawdown", getattr(momentum, "max_drawdown", None))
        put("sharpe ratio", getattr(momentum, "sharpe_ratio", None))
    dcf = frameworks.get("dcf")
    if dcf is not None:
        put("dcf value", dcf.intrinsic_value_per_share)
        put("dcf margin of safety", dcf.margin_of_safety)

    metrics = analysis.get("metrics", {})
    for label, key in [
        ("P/E", "pe_ratio"), ("P/B", "pb_ratio"), ("ROE", "roe"),
        ("debt to equity", "debt_equity"), ("current ratio", "current_ratio"),
        ("dividend yield", "dividend_yield"), ("market cap", "market_cap"),
        ("eps", "eps"), ("book value", "book_value"), ("beta", "beta"),
    ]:
        put(label, metrics.get(key))

    confidence = analysis.get("data_confidence")
    if confidence is not None:
        put("data confidence", confidence.level)
    return snap


def _lens_detail(analysis: Optional[Dict[str, Any]], lens: str) -> Dict[str, Any]:
    """Per-criterion breakdown for one lens, as JSON-safe primitives."""
    if not analysis:
        return {"error": "no analysis loaded"}
    frameworks = analysis.get("frameworks", {})
    lens = (lens or "").lower()

    if lens == "composite":
        c = frameworks.get("composite")
        if c is None:
            return {"error": "no composite available"}
        return {
            "overall_score": c.overall_score,
            "profile": c.profile,
            "lenses": {
                k: {
                    "score": c.lens_scores.get(k),
                    "weight": c.weights.get(k),
                    "rating": c.lens_ratings.get(k),
                    "verdict": c.lens_verdicts.get(k),
                }
                for k in c.lens_scores
            },
        }

    if lens == "value":
        v = analysis.get("valuation", {})
        return {
            "score": frameworks.get("composite").lens_scores.get("value")
            if frameworks.get("composite") else None,
            "avg_intrinsic_value": v.get("avg_intrinsic_value"),
            "current_price": analysis.get("current_price"),
            "methods": {
                "graham_number": v.get("graham_number"),
                "ncav_per_share": v.get("ncav_per_share"),
                "normalized_value": v.get("normalized_value"),
                "dividend_adjusted_value": v.get("dividend_adjusted_value"),
            },
            "margins_of_safety": v.get("margins_of_safety", {}),
        }

    obj = frameworks.get(lens)
    if obj is None:
        return {"error": f"unknown lens {lens!r}",
                "available": ["value", "quality", "growth", "dividend", "momentum", "composite"]}
    return {
        "score": getattr(obj, "score", None),
        "rating": getattr(obj, "rating", None) or getattr(obj, "signal", None),
        "checks": getattr(obj, "checks", {}),
    }
