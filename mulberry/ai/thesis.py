"""
AI investment-thesis synthesis

Turns Mulberry's computed metrics — composite score, per-lens verdicts, key
metrics, and the SEC-filing context extracted in the filings engine — into a
written narrative: a thesis, a bull case, a bear case, and flagged risks.

The narrative is **advisory prose only**: it never alters the numeric scores or
the recommendation, and the report labels it as model-generated. Generation is
optional — without an Anthropic API key the section is simply omitted and the
rest of the analysis is unaffected.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are an equity research analyst writing an internal research note. "
    "You are given pre-computed quantitative analysis of a public company "
    "(multi-framework scores, valuation margins, trends from SEC filings, and "
    "excerpts from the latest filing). Synthesize ONLY the provided data — do "
    "not invent figures, and do not contradict the computed scores. Write in "
    "measured, professional prose. This is educational research context, not "
    "personalized investment advice, and must never say 'you should buy/sell'."
)

# Structured-output schema: guarantees parseable narrative fields.
THESIS_SCHEMA = {
    "type": "object",
    "properties": {
        "thesis": {
            "type": "string",
            "description": "3-5 sentence core investment thesis synthesizing the strongest signals across frameworks",
        },
        "bull_case": {
            "type": "string",
            "description": "2-4 sentence strongest credible case for the stock outperforming",
        },
        "bear_case": {
            "type": "string",
            "description": "2-4 sentence strongest credible case for the stock underperforming",
        },
        "risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "3-6 specific, concrete risk factors grounded in the provided data",
        },
    },
    "required": ["thesis", "bull_case", "bear_case", "risks"],
    "additionalProperties": False,
}


@dataclass
class ThesisResult:
    """Model-generated narrative synthesis."""
    thesis: str
    bull_case: str
    bear_case: str
    risks: List[str] = field(default_factory=list)
    model: str = ""


class ThesisGenerator:
    """
    Generates an investment-thesis narrative via the Anthropic API.

    Degrades gracefully: if no API key is configured or the call fails for any
    reason, ``generate`` returns None and the caller omits the section.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None,
                 client=None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("THESIS_MODEL", "") or DEFAULT_MODEL
        self._client = client  # injectable for tests

    @property
    def available(self) -> bool:
        return self._client is not None or bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def generate(self, analysis: Dict[str, Any]) -> Optional[ThesisResult]:
        """Synthesize a narrative from an analysis result dict, or None."""
        if not self.available:
            logger.info("Thesis generation skipped: no ANTHROPIC_API_KEY configured")
            return None

        payload = build_payload(analysis)

        try:
            import anthropic
        except ImportError:
            logger.warning("Thesis generation skipped: `anthropic` package not installed")
            return None

        try:
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=8000,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                output_config={"format": {"type": "json_schema", "schema": THESIS_SCHEMA}},
                messages=[{
                    "role": "user",
                    "content": (
                        "Write the research note for the following computed "
                        "analysis:\n\n" + json.dumps(payload, indent=2, default=str)
                    ),
                }],
            )
            if response.stop_reason == "refusal":
                logger.warning("Thesis generation declined by the model")
                return None
            text = next((b.text for b in response.content if b.type == "text"), "")
            data = json.loads(text)
            return ThesisResult(
                thesis=data["thesis"],
                bull_case=data["bull_case"],
                bear_case=data["bear_case"],
                risks=list(data.get("risks", [])),
                model=response.model,
            )
        except anthropic.AuthenticationError:
            logger.warning("Thesis generation skipped: invalid Anthropic API key")
            return None
        except Exception as e:
            logger.warning(f"Thesis generation failed: {e}")
            return None


# ---------------------------------------------------------------------------
# Payload construction (pure — unit-tested directly)
# ---------------------------------------------------------------------------

def build_payload(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Distill the analysis result into a compact, structured payload.

    Only computed values go in — the model synthesizes, it never computes.
    """
    frameworks = analysis.get("frameworks", {})
    composite = frameworks.get("composite")
    valuation = analysis.get("valuation", {})
    metrics = analysis.get("metrics", {})
    confidence = analysis.get("data_confidence")

    payload: Dict[str, Any] = {
        "symbol": analysis.get("symbol", ""),
        "company": analysis.get("company_info", {}).get("name", ""),
        "sector": analysis.get("company_info", {}).get("sector", ""),
        "industry": analysis.get("company_info", {}).get("industry", ""),
        "current_price": analysis.get("current_price", 0),
        "recommendation": analysis.get("recommendation", ""),
        "margins_of_safety": valuation.get("margins_of_safety", {}),
        "avg_intrinsic_value": valuation.get("avg_intrinsic_value", 0),
        "key_metrics": {
            k: metrics.get(k)
            for k in ("pe_ratio", "pb_ratio", "market_cap", "roe",
                      "debt_equity", "current_ratio", "dividend_yield")
            if metrics.get(k) is not None
        },
    }

    if composite is not None:
        payload["composite"] = {
            "overall_score": composite.overall_score,
            "profile": composite.profile,
            "lens_scores": composite.lens_scores,
            "lens_ratings": composite.lens_ratings,
            "lens_verdicts": composite.lens_verdicts,
        }

    if confidence is not None:
        payload["data_confidence"] = {
            "level": confidence.level,
            "notes": list(confidence.notes),
        }

    peer = analysis.get("peer_comparison")
    if peer is not None:
        payload["peer_comparison"] = {
            "peers": list(peer.peer_symbols),
            "overall_percentile": peer.overall_percentile,
        }

    filings = analysis.get("filings")
    if filings is not None:
        payload["sec_filings"] = {
            "red_flags": [
                {"label": f.label, "severity": f.severity, "detail": f.detail}
                for f in filings.red_flags
            ],
            "trends": [
                {"metric": t.label, "direction": t.direction,
                 "change_pct": round(t.change_pct, 3),
                 "favorable": (t.direction == "Rising") == t.higher_is_better
                 if t.direction != "Flat" else None}
                for t in filings.trends
            ],
            "filing_excerpts": [
                # Truncate defensively; excerpts are already ~1200 chars
                {"section": s.title, "excerpt": s.excerpt[:1500]}
                for s in filings.sections
            ],
            "days_since_last_periodic": filings.days_since_last_periodic,
        }

    return payload
