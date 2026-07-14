"""Translation layer: turn a detected event/change into a structured legal memo item.

This is the product. Detection tells us *something changed*; this layer answers
*what should infrastructure counsel do about it, and by when* — by applying the
materiality rubric (the system prompt below) via one Claude API call per finding
and returning structured JSON.

Design choices:
* Model `claude-opus-4-8` with adaptive thinking at high effort — legal
  materiality judgment is correctness-sensitive, not a place to economize.
* Structured output via `output_config.format` (json_schema) guarantees every
  memo item is parseable — no prompt-and-pray JSON.
* Date arithmetic is done in Python (radar.sla_util), not by the model. We
  pre-compute the estimated SLA claim deadline from the event date and hand it
  to the model as a fact. Models are unreliable at "end of the second billing
  cycle after March" style math; code is not.
* One finding = one call. Findings are independent, so this keeps each prompt
  focused and each memo item auditable.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

MODEL = "claude-opus-4-8"

# The legal materiality rubric, encoded as operating instructions for the model.
SYSTEM_PROMPT = """\
You are an issue-spotting assistant for an in-house technology transactions \
attorney who manages hyperscaler (AWS) relationships. You translate detected \
AWS operational events and legal-document changes into concrete legal action \
items with deadlines. You write as counsel, for counsel: terse, specific, no \
filler. You screen and triage; you do NOT conclude legal eligibility.

Apply this rubric to the single finding you are given.

A. OPERATIONAL EVENTS (from the AWS Health feed):
 1. SLA credit eligibility screening. Using the stored SLA thresholds provided \
to you, decide whether the event could plausibly push monthly uptime below a \
credit threshold for affected workloads. If so, set potentially_credit_eligible \
true and state which SLA applies, the credit tiers, and the claim deadline. Use \
the ESTIMATED CLAIM DEADLINE provided in the finding data verbatim as \
estimated_claim_deadline — do not compute your own date. If no deadline was \
provided or it cannot be determined, say so in deadline_basis and instruct the \
user to check the SLA claim terms rather than guessing.
 2. Data residency exposure. If an event hit an entire region or AZ capacity, \
flag that engineering failover to another region during the event may implicate \
data residency / transfer commitments (DPAs, SCCs, residency promises). Action: \
confirm with engineering whether cross-region failover occurred in the window.
 3. Downstream commitment exposure. For sustained or multi-service events, note \
the customer's own downstream SLAs kept running: quantify customer-facing \
impact, review force majeure / upstream-provider-failure exclusions in the \
customer agreements, and preserve incident documentation now.
 4. Capacity events. For launch failures / capacity constraints, flag that \
engineering workarounds (region shifts, instance-type changes, emergency \
reservations) create contract/compliance facts without legal involvement. \
Action: ask engineering what changed in the window.

B. TERMS / SLA PAGE CHANGES (from diffs):
 1. Classify each substantive change by what it touches: liability/indemnity, \
data handling/privacy, service commitments/SLA thresholds/credit structure, \
termination/suspension, IP/license scope, AI/ML-specific terms, pricing in \
terms. A change touching none of these (formatting, typos, contacts) is NOISE.
 2. For a material change: quote short old and new excerpts, explain in 2-3 \
sentences what it means for a customer, and give a recommended action.
 3. An SLA threshold or credit-structure change is the highest-value catch \
this tool exists for — treat it as URGENT/REVIEW, never NOISE.

C. OUTPUT DISCIPLINE:
 - materiality is URGENT (deadline within 30 days OR active/ongoing exposure), \
REVIEW (material, no immediate deadline), or NOISE (appendix).
 - Every URGENT item MUST carry a date in an action item or the credit screening.
 - State confidence and caveats honestly. You do not conclude eligibility.
 - Weight relevance by the user's watchlist if provided; if absent, report fully.

Return ONLY the structured object required by the schema. Leave \
sla_credit_screening null for non-operational findings. Populate quoted_changes \
only for terms/SLA changes."""

# Structured-output schema. Every field required; nullable where a value may
# legitimately be absent (e.g. an action item with no deadline).
_MEMO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "headline": {"type": "string"},
        "classification": {
            "type": "string",
            "enum": ["operational_event", "terms_change", "sla_change", "noise"],
        },
        "materiality": {"type": "string", "enum": ["URGENT", "REVIEW", "NOISE"]},
        "materiality_rationale": {"type": "string"},
        "what_happened": {"type": "string"},
        "why_counsel_cares": {"type": "string"},
        "sla_credit_screening": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "potentially_credit_eligible": {"type": "boolean"},
                "applicable_sla": {"type": "string"},
                "credit_tiers": {"type": "string"},
                "estimated_claim_deadline": {"type": "string"},
                "deadline_basis": {"type": "string"},
            },
            "required": [
                "potentially_credit_eligible",
                "applicable_sla",
                "credit_tiers",
                "estimated_claim_deadline",
                "deadline_basis",
            ],
        },
        "quoted_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "old_language": {"type": "string"},
                    "new_language": {"type": "string"},
                    "category": {"type": "string"},
                    "meaning_for_customer": {"type": "string"},
                },
                "required": [
                    "old_language",
                    "new_language",
                    "category",
                    "meaning_for_customer",
                ],
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "action": {"type": "string"},
                    "deadline": {"type": ["string", "null"]},
                    "suggested_owner": {"type": "string"},
                },
                "required": ["action", "deadline", "suggested_owner"],
            },
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "caveats": {"type": "string"},
    },
    "required": [
        "headline",
        "classification",
        "materiality",
        "materiality_rationale",
        "what_happened",
        "why_counsel_cares",
        "sla_credit_screening",
        "quoted_changes",
        "action_items",
        "confidence",
        "caveats",
    ],
}


def _extract_json(response) -> Dict[str, Any]:
    """With output_config.format, the first text block is guaranteed valid JSON.
    Thinking blocks may precede it, so pick the text block explicitly."""
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("No text block in model response.")
    return json.loads(text)


def translate_finding(
    client, finding: Dict[str, Any]
) -> Dict[str, Any]:
    """Run one finding through the rubric. Returns the finding dict enriched
    with a `memo` key holding the parsed structured item."""
    user_content = (
        "Apply the rubric to this single finding and return the structured "
        "object.\n\nFINDING DATA (JSON):\n"
        + json.dumps(finding["payload"], indent=2, ensure_ascii=False)
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": _MEMO_SCHEMA},
        },
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    memo = _extract_json(response)
    return {**finding, "memo": memo}


def translate_all(
    client, findings: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Translate every finding, tolerating individual failures so one bad call
    doesn't sink the whole memo."""
    items: List[Dict[str, Any]] = []
    for f in findings:
        try:
            items.append(translate_finding(client, f))
        except Exception as exc:
            items.append({**f, "error": str(exc)})
    return items
