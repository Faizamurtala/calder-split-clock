# Google Form draft — Calder Split-Clock

**Project name:** Calder Split-Clock  
**One-line (≤140):** Two-clock agent for tokenized US stocks: it only trades when the 7×24 rToken tape disagrees with the dark Wall Street clock.  
**Track:** Agentic Trading  
**Sub-theme:** Event-Driven Agent  
**Builder name on X / form:** Wren Calder (use your real Bitget UID / X handle)

---

## Project Description (paste into the form)

### 1. Thesis
US cash equities sleep. Bitget rTokens do not. That split creates a new kind of event-driven tape: headlines, geopolitics and crypto beta can reprice NVDA, TSLA, QQQ on Saturday while the primary market is closed.

Most agents treat that tape as “just another chart.” Calder treats it as two clocks.

- Wall Street clock = price discovery.
- Chain clock = 7×24 rToken prints.

The agent classifies every name into one regime: DISCOVERY, INFO_PRICE, TAPE_NOISE, CRYPTO_BLEED, OPEN_TRAP. Only INFO_PRICE (and a rare cash-hours catalyst) may become a ticket. CRYPTO_BLEED and OPEN_TRAP are hard vetoes. Every accepted ticket carries a stop, a take, and an expiry that dies before or at the next cash open unless the thesis is renewed.

The LLM is a clerk. It may rewrite the English. It may not change side, size, stop or regime. If the model is offline, the desk still runs.

### 2. Target user and product value
Not “all traders.”

Primary user: a crypto-native Bitget user, $3k–$30k, who already holds or wants rNVDA / rTSLA / rQQQ, is awake in Africa / Asia / Europe when NY is closed, and currently either FOMO-buys weekend spikes or stays flat and misses real information pricing.

Pain: they cannot tell a real after-hours catalyst from BTC dragging high-beta names. Existing bots shout BUY. Calder returns WAIT with a reason and a kill time.

### 3. Validation data and key metrics
Current validation is paper-only (hackathon-correct).

- Universe: NVDA, TSLA, AAPL, MSFT, AMZN, META, AMD, QQQ
- Engine: session classifier + residual vs QQQ + BTC-bleed veto + headline alignment + risk cage
- Starter seeded book + live cycles from first deploy
- Metrics the log actually stores: decisions, accept rate, realized PnL, win rate, stop / take / expiry exits
- Targets (labelled targets, not claims): 2 weeks of unattended 30-minute cycles, accept rate < 25%, max drawdown < 4% of paper equity, no weekend hold into Monday without a still-live catalyst

Fee and slippage are modelled as 0 in the first paper book and will be added when Hub paper endpoints are wired.

### 4. Progress
Built: clock officer, split-clock classifier, risk cage, optional LLM clerk, FastAPI desk, paper JSONL ledger, one-cycle CLI, deploy files.

Not built yet: live Bitget rToken marks via Agent Hub, true 14-day unattended run, fee model.

Next: hook Hub `--paper-trading`, keep Yahoo as fallback, let the loop run through 27 Sep.

Frameworks: Python, FastAPI, yfinance + RSS for perception, optional OpenAI-compatible LLM (Qwen via Bitget gateway if credits arrive).

### 5. Deliverables
- Public demo URL (after you deploy)
- This repo
- `data/paper_log.jsonl` and `data/book_state.json`
- `docs/SUBMISSION.md` (this file)
- X post with #BitgetHackathon @Bitget_AI

### 6. Take on AI trading
Agentic trading fails when the model is the gambler. It works when the model is a clerk sitting behind a session clock and a cage. Tokenized US stocks make that split obvious: the hours themselves are the signal.

## Role of the LLM
Default path uses no LLM. The brain is deterministic.

If `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL` are set (Qwen `qwen3.8-max` at `https://hackathon.bitgetops.com/v1` or any OpenAI-compatible endpoint), the model only polishes `reason` and `contra`. Side, size, stop, regime stay locked in `app/risk.py` and `app/signals.py`.
