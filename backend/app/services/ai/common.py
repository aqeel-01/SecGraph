"""Shared provider request helpers."""

import json
from typing import Any, Mapping


def context_prompt(context: Mapping[str, Any]) -> str:
    """Serialize only the supplied compact context into an analysis prompt."""

    payload = json.dumps(
        context,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (
        "Task: perform a security analysis of the supplied API finding.\n"
        "Use only the relevant endpoint, source, and relationships in CONTEXT. "
        "Do not invent code behavior, data flow, controls, or attack impact. "
        "Clearly distinguish confirmed evidence from a possible or suspected "
        "issue; use cautious language when evidence is incomplete.\n"
        "Return ONLY valid JSON with exactly these fields: "
        "severity, confidence, explanation, potential_attack, impact, "
        "suggested_fix. Severity must be one of critical, high, medium, low, "
        "or informational. Confidence must be a number from 0 to 1.\n"
        f"CONTEXT:{payload}"
    )
