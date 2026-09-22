"""Paper book. Every decision is appended to data/paper_log.jsonl."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .clock import classify_session, now_ny
from .data import fetch_snapshot, snapshot_dict
from .llm import polish
from .risk import RiskConfig, build_ticket, ticket_dict
from .signals import scan, verdict_dict

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "data" / "paper_log.jsonl"
STATE = ROOT / "data" / "book_state.json"


def _read_state() -> dict[str, Any]:
    if not STATE.exists():
        return {
            "equity": 10_000.0,
            "cash": 10_000.0,
            "positions": [],
            "closed": [],
            "decisions": 0,
            "accepted": 0,
        }
    return json.loads(STATE.read_text())


def _write_state(state: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def _append(row: dict[str, Any]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")


def mark_to_market(state: dict[str, Any], quotes: dict) -> dict[str, Any]:
    equity = state["cash"]
    live = []
    for p in state.get("positions", []):
        q = quotes.get(p["symbol"])
        px = q["price"] if q else p["entry"]
        sign = 1 if p["side"] == "BUY" else -1
        pnl_pct = sign * (px / p["entry"] - 1) * 100
        pnl_usd = p["qty_usd"] * pnl_pct / 100
        age_h = (
            datetime.now(timezone.utc) - datetime.fromisoformat(p["opened_at"].replace("Z", "+00:00"))
        ).total_seconds() / 3600
        exit_why = ""
        if pnl_pct <= -p["stop_pct"]:
            exit_why = "STOP"
        elif pnl_pct >= p["take_pct"]:
            exit_why = "TAKE"
        elif age_h >= p["expire_hours"]:
            exit_why = "EXPIRED"
        if exit_why:
            closed = {**p, "exit": px, "pnl_pct": round(pnl_pct, 3), "pnl_usd": round(pnl_usd, 2), "exit_why": exit_why}
            state.setdefault("closed", []).append(closed)
            state["cash"] += p["qty_usd"] + pnl_usd
            equity = state["cash"]
            _append({"type": "exit", "ts": datetime.now(timezone.utc).isoformat(), **closed})
        else:
            live.append({**p, "mark": px, "pnl_pct": round(pnl_pct, 3), "pnl_usd": round(pnl_usd, 2)})
            equity += p["qty_usd"] + pnl_usd
    state["positions"] = live
    state["equity"] = round(equity, 2)
    return state


def step(symbols: list[str], cfg: RiskConfig | None = None) -> dict[str, Any]:
    cfg = cfg or RiskConfig()
    session = classify_session()
    snap = fetch_snapshot(symbols)
    state = mark_to_market(_read_state(), {k: v.__dict__ for k, v in snap.quotes.items()})

    verdicts = scan(snap, session, symbols)
    tickets = []
    for v in verdicts:
        t = build_ticket(
            symbol=v.symbol,
            side=v.side,
            size_pct_hint=v.size_pct,
            regime=v.regime,
            confidence=v.confidence,
            expire_hours=v.expire_hours,
            reason=v.reason,
            contra=v.contra,
            session_code=session.code,
            liquidity=session.liquidity,
            open_positions=len(state["positions"]),
            cfg=cfg,
        )
        row = ticket_dict(t)
        row.update({"headline": v.headline, "gates": v.gates})
        row = polish(row, session.label)
        state["decisions"] = state.get("decisions", 0) + 1
        if t.accepted:
            state["accepted"] = state.get("accepted", 0) + 1
            q = snap.quotes[v.symbol]
            pos = {
                "symbol": v.symbol,
                "side": t.side,
                "qty_usd": t.qty_usd,
                "entry": q.price,
                "stop_pct": t.stop_pct,
                "take_pct": t.take_pct,
                "expire_hours": t.expire_hours,
                "regime": t.regime,
                "opened_at": datetime.now(timezone.utc).isoformat(),
            }
            state["positions"].append(pos)
            state["cash"] -= t.qty_usd
            _append({"type": "entry", "ts": datetime.now(timezone.utc).isoformat(), **row, "entry": q.price})
        else:
            _append({"type": "stand_down", "ts": datetime.now(timezone.utc).isoformat(), **row})
        tickets.append(row)

    _write_state(state)
    closed = state.get("closed", [])
    wins = [c for c in closed if c.get("pnl_usd", 0) > 0]
    pnl = sum(c.get("pnl_usd", 0) for c in closed)
    return {
        "session": session.__dict__,
        "ny_time": now_ny().strftime("%Y-%m-%d %H:%M %Z"),
        "snapshot": snapshot_dict(snap),
        "verdicts": [verdict_dict(v) for v in verdicts],
        "tickets": tickets,
        "book": {
            "equity": state["equity"],
            "cash": round(state["cash"], 2),
            "open": state["positions"],
            "closed_n": len(closed),
            "wins": len(wins),
            "win_rate": round(len(wins) / len(closed), 3) if closed else 0.0,
            "realized_pnl": round(pnl, 2),
            "decisions": state.get("decisions", 0),
            "accepted": state.get("accepted", 0),
        },
    }


def history(limit: int = 80) -> list[dict[str, Any]]:
    if not LOG.exists():
        return []
    rows = [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]
    return rows[-limit:]
