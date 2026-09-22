"""Market + news intake.

Live path uses Yahoo Finance (no Bitget key needed to demo).
If Yahoo is blocked, a seeded replay book still runs so the desk never dies.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import yfinance as yf
except Exception:  # pragma: no cover
    yf = None

try:
    import feedparser
except Exception:
    feedparser = None


WATCH = {
    "NVDA": {"name": "NVIDIA", "beta_qqq": 1.55, "crypto_beta": 0.35},
    "TSLA": {"name": "Tesla", "beta_qqq": 1.40, "crypto_beta": 0.45},
    "AAPL": {"name": "Apple", "beta_qqq": 1.10, "crypto_beta": 0.15},
    "MSFT": {"name": "Microsoft", "beta_qqq": 1.15, "crypto_beta": 0.18},
    "AMZN": {"name": "Amazon", "beta_qqq": 1.20, "crypto_beta": 0.20},
    "META": {"name": "Meta", "beta_qqq": 1.25, "crypto_beta": 0.22},
    "AMD": {"name": "AMD", "beta_qqq": 1.50, "crypto_beta": 0.30},
    "QQQ": {"name": "Nasdaq 100 ETF", "beta_qqq": 1.00, "crypto_beta": 0.25},
}

NEWS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA,TSLA,AAPL,MSFT,AMZN,META,AMD,QQQ&region=US&lang=en-US",
    "https://news.google.com/rss/search?q=Federal+Reserve+OR+FOMC+OR+tariff+OR+earnings+when:1d&hl=en-US&gl=US&ceid=US:en",
]


@dataclass
class Quote:
    symbol: str
    price: float
    change_pct: float
    volume_ratio: float
    source: str
    ts: str


@dataclass
class Headline:
    title: str
    source: str
    published: str
    symbols: list[str]
    kind: str  # earnings | macro | geo | product | unknown


@dataclass
class Snapshot:
    quotes: dict[str, Quote]
    headlines: list[Headline]
    btc_change_pct: float
    qqq_change_pct: float
    source: str
    generated_at: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _seeded_price(symbol: str, now: datetime) -> Quote:
    meta = WATCH[symbol]
    rng = random.Random(f"{symbol}-{now.strftime('%Y%m%d%H')}")
    base = {
        "NVDA": 128.4,
        "TSLA": 248.1,
        "AAPL": 228.6,
        "MSFT": 428.2,
        "AMZN": 198.4,
        "META": 572.0,
        "AMD": 164.3,
        "QQQ": 492.8,
    }[symbol]
    hour_wave = math.sin(now.hour / 24 * math.pi * 2 + hash(symbol) % 7) * 0.6
    shock = rng.uniform(-1.8, 1.8)
    chg = hour_wave + shock * (0.4 + meta["crypto_beta"])
    px = round(base * (1 + chg / 100), 2)
    vol = round(max(0.12, rng.uniform(0.2, 1.6)), 3)
    return Quote(symbol, px, round(chg, 3), vol, "replay-book", now.isoformat())


def fetch_quotes(symbols: list[str]) -> tuple[dict[str, Quote], str]:
    now = _utc_now()
    if yf is None:
        return {s: _seeded_price(s, now) for s in symbols}, "replay-book"
    out: dict[str, Quote] = {}
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for s in symbols:
            t = tickers.tickers.get(s)
            if t is None:
                out[s] = _seeded_price(s, now)
                continue
            hist = t.history(period="5d", interval="1h")
            if hist is None or hist.empty:
                info = getattr(t, "fast_info", None)
                last = float(getattr(info, "last_price", 0) or 0)
                if last <= 0:
                    out[s] = _seeded_price(s, now)
                    continue
                out[s] = Quote(s, round(last, 2), 0.0, 1.0, "yahoo-last", now.isoformat())
                continue
            last = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            chg = (last / prev - 1) * 100 if prev else 0.0
            vol = float(hist["Volume"].iloc[-1]) if "Volume" in hist else 0
            avg = float(hist["Volume"].tail(20).mean()) if "Volume" in hist else 1
            vr = vol / avg if avg else 1.0
            out[s] = Quote(s, round(last, 2), round(chg, 3), round(vr, 3), "yahoo-1h", now.isoformat())
        return out, "yahoo"
    except Exception:
        return {s: _seeded_price(s, now) for s in symbols}, "replay-book"


def _classify_headline(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("earnings", "eps", "guidance", "revenue", "beat", "miss")):
        return "earnings"
    if any(k in t for k in ("fed", "fomc", "rate", "cpi", "inflation", "payroll", "treasury")):
        return "macro"
    if any(k in t for k in ("tariff", "war", "sanction", "geopolit", "israel", "china", "export")):
        return "geo"
    if any(k in t for k in ("launch", "chip", "model", "gpt", "product", "recall")):
        return "product"
    return "unknown"


def _hit_symbols(title: str) -> list[str]:
    up = title.upper()
    hits = [s for s in WATCH if s in up or WATCH[s]["name"].upper() in up]
    if any(k in title.lower() for k in ("nasdaq", "tech", "magnificent", "semiconductor")):
        hits = list(dict.fromkeys(hits + ["QQQ", "NVDA", "AMD"]))
    if any(k in title.lower() for k in ("fed", "fomc", "cpi", "tariff")):
        hits = list(dict.fromkeys(hits + ["QQQ"]))
    return hits[:6]


def fetch_headlines(limit: int = 12) -> list[Headline]:
    items: list[Headline] = []
    if feedparser is None:
        return _fallback_headlines()
    for url in NEWS_FEEDS:
        try:
            parsed = feedparser.parse(url)
            for e in parsed.entries[:10]:
                title = (e.get("title") or "").strip()
                if not title:
                    continue
                items.append(
                    Headline(
                        title=title[:220],
                        source=(e.get("source", {}) or {}).get("title") or parsed.feed.get("title") or "rss",
                        published=str(e.get("published") or e.get("updated") or _utc_now().isoformat()),
                        symbols=_hit_symbols(title),
                        kind=_classify_headline(title),
                    )
                )
        except Exception:
            continue
    if not items:
        return _fallback_headlines()
    # de-dupe
    seen = set()
    unique = []
    for h in items:
        key = h.title.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        unique.append(h)
    return unique[:limit]


def _fallback_headlines() -> list[Headline]:
    now = _utc_now().isoformat()
    return [
        Headline("Fed speakers keep rate-cut path data-dependent into next week", "replay", now, ["QQQ"], "macro"),
        Headline("Semiconductor export controls remain a weekend headline risk for NVDA and AMD", "replay", now, ["NVDA", "AMD"], "geo"),
        Headline("Tesla delivery chatter mixed into thin after-hours tape", "replay", now, ["TSLA"], "product"),
    ]


def fetch_snapshot(symbols: list[str]) -> Snapshot:
    quotes, src = fetch_quotes(symbols + (["QQQ"] if "QQQ" not in symbols else []))
    headlines = fetch_headlines()
    qqq = quotes.get("QQQ")
    # crude BTC proxy: if yahoo available try BTC-USD else synthetic
    btc = 0.0
    if yf is not None:
        try:
            hist = yf.Ticker("BTC-USD").history(period="2d", interval="1h")
            if hist is not None and len(hist) > 1:
                btc = float((hist["Close"].iloc[-1] / hist["Close"].iloc[-2] - 1) * 100)
        except Exception:
            btc = 0.0
    if btc == 0.0:
        btc = round(random.Random(_utc_now().strftime("%Y%m%d%H")).uniform(-1.2, 1.2), 3)
    return Snapshot(
        quotes=quotes,
        headlines=headlines,
        btc_change_pct=round(btc, 3),
        qqq_change_pct=qqq.change_pct if qqq else 0.0,
        source=src,
        generated_at=_utc_now().isoformat(),
    )


def snapshot_dict(snap: Snapshot) -> dict[str, Any]:
    return {
        "quotes": {k: v.__dict__ for k, v in snap.quotes.items()},
        "headlines": [h.__dict__ for h in snap.headlines],
        "btc_change_pct": snap.btc_change_pct,
        "qqq_change_pct": snap.qqq_change_pct,
        "source": snap.source,
        "generated_at": snap.generated_at,
    }
