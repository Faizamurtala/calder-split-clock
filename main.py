from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from clock import Session, hours_to_next_cash_open
from paper import history, step
from risk import RiskConfig

load_dotenv()

ROOT = Path(__file__).resolve().parent
WEB = ROOT

SYMBOLS = [s.strip().upper() for s in os.getenv("CALDER_SYMBOLS", "NVDA,TSLA,AAPL,MSFT,AMZN,META,AMD,QQQ").split(",") if s.strip()]
CFG = RiskConfig(
    equity=float(os.getenv("CALDER_EQUITY", "10000")),
    risk_pct=float(os.getenv("CALDER_RISK_PCT", "0.75")),
    max_positions=int(os.getenv("CALDER_MAX_POS", "3")),
)

app = FastAPI(title="Calder Split-Clock", version="1.0.0")

@app.get("/")
def index():
    return FileResponse(WEB / "index.html")

@app.get("/api/health")
def health():
    s = classify_session()
    return {
        "ok": True,
        "agent": "Calder Split-Clock",
        "builder": "Wren Calder",
        "ny": now_ny().strftime("%Y-%m-%d %H:%M %Z"),
        "session": s.code,
        "hours_to_cash_open": round(hours_to_next_cash_open(), 2),
        "mode": os.getenv("CALDER_MODE", "paper"),
    }

@app.get("/api/scan")
def api_scan():
    return JSONResponse(step(SYMBOLS, CFG))

@app.get("/api/log")
def api_log(limit: int = 80):
    return {"rows": history(limit)}
