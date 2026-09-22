#!/usr/bin/env python3
"""One paper cycle. Run on a cron every 15–30 minutes during the hackathon."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app.paper import step
from app.risk import RiskConfig

SYMBOLS = [s.strip().upper() for s in os.getenv("CALDER_SYMBOLS", "NVDA,TSLA,AAPL,MSFT,AMZN,META,AMD,QQQ").split(",") if s.strip()]
CFG = RiskConfig(
    equity=float(os.getenv("CALDER_EQUITY", "10000")),
    risk_pct=float(os.getenv("CALDER_RISK_PCT", "0.75")),
    max_positions=int(os.getenv("CALDER_MAX_POS", "3")),
)


def main() -> None:
    out = step(SYMBOLS, CFG)
    book = out["book"]
    sess = out["session"]
    print(f"[{out['ny_time']}] session={sess['code']} liq={sess['liquidity']}")
    print(f"equity={book['equity']} cash={book['cash']} open={len(book['open'])} realized={book['realized_pnl']} wr={book['win_rate']}")
    for t in out["tickets"]:
        flag = "TAKE" if t["accepted"] else "WAIT"
        print(f"  {flag:4} {t['symbol']:5} {t['side']:8} {t['regime']:12} conf={t['confidence']}  {t['reason'][:90]}")
    Path(ROOT / "data" / "last_scan.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
