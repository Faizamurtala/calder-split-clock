# Calder Split-Clock

**Builder:** Wren Calder  
**Track:** Agentic Trading → Event-Driven Agent  
**Market:** Tokenized US stocks (rTokens) that trade when NY is dark  
**Mode:** Paper first. Live Agent Hub later.

Most AI trading bots ask a model “buy or sell?” and hope.

Calder does not.

Tokenized US stocks live on **two clocks**:

1. **Wall Street clock** — cash hours, real price discovery  
2. **Chain clock** — Bitget rToken tape, 7×24, including weekends  

A move is only a trade when those clocks **disagree**.  
If rNVDA rips on Saturday because BTC ripped, that is costume, not equity.  
If rNVDA reprices a real export-control headline while NY is closed, that is the 7×24 job.

```
News / tape
    │
    ▼
Clock officer ── session: CASH | PRE | AH | NIGHT | WEEKEND
    │
    ▼
Split-clock classifier
    DISCOVERY | INFO_PRICE | TAPE_NOISE | CRYPTO_BLEED | OPEN_TRAP
    │
    ▼
Risk cage ── size, stop, expiry, book limits
    │
    ▼
LLM clerk (optional) ── may rewrite words, never side or size
    │
    ▼
Paper book ── entry / stand-down / stop / take / expiry
```

## Why this is not MacroVex / Sentinel / AfterHours copies

| Them | Calder |
|---|---|
| Chart + SMC/ICT stack | No chart religion. Session + clock disagreement. |
| AI argues with itself | Rules name the regime first. Model is a clerk. |
| After-hours z-score mean reversion | We do **not** auto-fade every spike. We ask *which clock printed*. |
| Generic buy/sell bot | Every ticket has a **kill time**. Thesis dies at cash open unless renewed. |

## Quick start (laptop)

```bash
cd calder-split-clock
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed_history.py
python scripts/run_paper.py
uvicorn app.main:app --reload --port 8000
```

Open http://127.0.0.1:8000 and press **RUN ONE CYCLE**.

## Deploy (the path that just works)

Use **Render** or **Railway**. Both take this repo as-is.

### Render (recommended for the demo)

1. Push this folder to a public GitHub repo.  
2. [render.com](https://render.com) → New → Web Service → that repo.  
3. Settings:
   - Runtime: Python 3
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add env vars from `.env.example` (`CALDER_MODE=paper` is enough).  
5. Deploy. You get a public URL. That URL is your Demo.

Keep the paper loop alive:

- Render cron job **or**
- GitHub Action every 30 minutes calling `/api/scan`  
  (or run `python scripts/run_paper.py` on any always-on box)

### Railway

```text
railway init
railway up
```

Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Docker

```bash
docker build -t calder .
docker run -p 8000:8000 --env-file .env calder
```

## Hook Bitget Agent Hub later (not required to demo)

Paper logs are valid for the Agentic track. When you have an Agentic account:

1. Paste this into Claude / Cursor:

```
Please read https://www.bitget.careers/support/articles/12560603894122
and help me complete the Bitget Agentic account authorization process.
```

2. Run Hub in `--paper-trading` or `--read-only` first.  
3. Replace the Yahoo quotes in `app/data.py` with Hub marks for rNVDA / rTSLA / rQQQ.  
4. Keep Calder’s clock + cage. Do not let the model place size.

## What judges should click

- Demo: the deployed URL  
- Code: this repo  
- Logs: `data/paper_log.jsonl`  
- One-cycle proof: `python scripts/run_paper.py`

## Honest note on “profit”

No 5-day hackathon agent is a money machine. Calder is built to **refuse bad hours**.  
Standing down is a position. That is the edge we are testing.
