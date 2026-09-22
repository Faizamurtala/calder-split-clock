"""Optional LLM layer.

The model is a clerk, not a gambler.
It may rewrite the reason / contra in plain English.
It may NEVER change side, size, stop, or regime.
If the API is missing, we skip it and the rule brain still runs.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


SYSTEM = """You are the desk clerk for Calder Split-Clock, a paper-trading agent.
You receive a structured ticket. Rewrite ONLY:
- reason: 2 short sentences, trader English, no hype
- contra: 1 sentence that would kill the ticket
Do not change side, size, regime, or confidence.
Return JSON: {"reason": "...", "contra": "..."}.
If side is NO_TRADE, explain why standing down is the trade.
"""


def _client_config() -> tuple[str, str, str] | None:
    key = os.getenv("LLM_API_KEY", "").strip()
    base = os.getenv("LLM_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("LLM_MODEL", "").strip()
    if not key or not base or not model:
        return None
    return base, model, key


def polish(ticket: dict[str, Any], session_label: str) -> dict[str, Any]:
    cfg = _client_config()
    ticket.setdefault("llm_used", False)
    if cfg is None:
        return ticket
    base, model, key = cfg
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "session": session_label,
                        "symbol": ticket.get("symbol"),
                        "side": ticket.get("side"),
                        "regime": ticket.get("regime"),
                        "reason": ticket.get("reason"),
                        "contra": ticket.get("contra"),
                    }
                ),
            },
        ],
    }
    url = base + "/chat/completions"
    try:
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20.0,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
            if isinstance(data.get("reason"), str) and data["reason"].strip():
                ticket["reason"] = data["reason"].strip()[:400]
            if isinstance(data.get("contra"), str) and data["contra"].strip():
                ticket["contra"] = data["contra"].strip()[:240]
            ticket["llm_used"] = True
    except Exception as exc:
        ticket["llm_error"] = str(exc)[:180]
    return ticket
