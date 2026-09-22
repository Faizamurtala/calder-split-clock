#!/usr/bin/env python3
"""Build a starter paper log so the demo is not empty on first open."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.paper import LOG, STATE


def main() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if LOG.exists() and LOG.stat().st_size > 0:
        print("log already exists, skip seed")
        return
    t0 = datetime.now(timezone.utc) - timedelta(hours=36)
    rows = [
        {"type": "stand_down", "ts": (t0 + timedelta(hours=2)).isoformat(), "symbol": "TSLA", "side": "NO_TRADE", "regime": "CRYPTO_BLEED", "accepted": False, "reject_reason": "Veto: move is crypto-bleed without an equity catalyst.", "reason": "TSLA printed +1.1% with BTC +1.4% and no Tesla headline. Costume, not thesis.", "confidence": 0.4, "qty_usd": 0},
        {"type": "entry", "ts": (t0 + timedelta(hours=8)).isoformat(), "symbol": "NVDA", "side": "SELL", "regime": "INFO_PRICE", "accepted": True, "reason": "Weekend export-control headline + NVDA −0.9% residual vs QQQ on thin but not dead tape.", "contra": "Cash-open squeeze or official denial.", "confidence": 0.58, "qty_usd": 420, "entry": 129.1, "stop_pct": 1.6, "take_pct": 2.4, "expire_hours": 14},
        {"type": "exit", "ts": (t0 + timedelta(hours=19)).isoformat(), "symbol": "NVDA", "side": "SELL", "entry": 129.1, "exit": 127.4, "pnl_pct": 1.316, "pnl_usd": 5.53, "exit_why": "TAKE", "qty_usd": 420},
        {"type": "stand_down", "ts": (t0 + timedelta(hours=22)).isoformat(), "symbol": "AAPL", "side": "NO_TRADE", "regime": "OPEN_TRAP", "accepted": False, "reason": "4.2h to cash open. Friday night print is usually Monday food.", "confidence": 0.45, "qty_usd": 0},
        {"type": "entry", "ts": (t0 + timedelta(hours=28)).isoformat(), "symbol": "AMD", "side": "BUY", "regime": "INFO_PRICE", "accepted": True, "reason": "Product/export follow-through with AMD +0.7% after cash close.", "contra": "Gap-down through entry at 09:30.", "confidence": 0.52, "qty_usd": 310, "entry": 163.8, "stop_pct": 1.6, "take_pct": 2.4, "expire_hours": 10},
        {"type": "exit", "ts": (t0 + timedelta(hours=34)).isoformat(), "symbol": "AMD", "side": "BUY", "entry": 163.8, "exit": 162.9, "pnl_pct": -0.549, "pnl_usd": -1.70, "exit_why": "EXPIRED", "qty_usd": 310},
    ]
    with LOG.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    STATE.write_text(json.dumps({
        "equity": 10003.83,
        "cash": 10003.83,
        "positions": [],
        "closed": [
            {"symbol": "NVDA", "side": "SELL", "qty_usd": 420, "entry": 129.1, "exit": 127.4, "pnl_pct": 1.316, "pnl_usd": 5.53, "exit_why": "TAKE"},
            {"symbol": "AMD", "side": "BUY", "qty_usd": 310, "entry": 163.8, "exit": 162.9, "pnl_pct": -0.549, "pnl_usd": -1.70, "exit_why": "EXPIRED"},
        ],
        "decisions": 6,
        "accepted": 2,
    }, indent=2))
    print("seeded", LOG)


if __name__ == "__main__":
    main()
