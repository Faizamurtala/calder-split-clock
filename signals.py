"""Split-clock signal.

We do not ask the model 'buy or sell?'.
We first name WHAT KIND of move this is:

  DISCOVERY   — cash market is open, treat as ordinary equity tape
  INFO_PRICE  — cash closed, headline + move aligned, volume not dead
  TAPE_NOISE  — cash closed, move with no catalyst and thin volume
  CRYPTO_BLEED— rToken moving with BTC more than with its own story
  OPEN_TRAP   — close to Monday / cash open, gap risk dominates

Only INFO_PRICE (and rare DISCOVERY continuation) may produce a ticket.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from clock import Session, hours_to_next_cash_open
from data import Headline, Quote, Snapshot, WATCH


@dataclass
class Verdict:
    symbol: str
    side: str  # BUY | SELL | NO_TRADE
    regime: str
    confidence: float
    size_pct: float
    reason: str
    contra: str
    expire_hours: float
    gates: dict[str, bool]
    headline: str


def _best_headline(symbol: str, headlines: list[Headline]) -> Headline | None:
    scored: list[tuple[int, Headline]] = []
    for h in headlines:
        score = 0
        if symbol in h.symbols:
            score += 3
        if h.kind in ("earnings", "macro", "geo"):
            score += 2
        if h.kind == "product":
            score += 1
        if score:
            scored.append((score, h))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _direction_from_headline(h: Headline | None) -> str:
    if h is None:
        return "NONE"
    t = h.title.lower()
    bear = ("cut", "miss", "ban", "tariff", "war", "downgrade", "probe", "delay", "weak", "slowdown")
    bull = ("beat", "raise", "upgrade", "surge", "record", "approval", "strong", "buyback")
    b = sum(1 for k in bear if k in t)
    u = sum(1 for k in bull if k in t)
    if u > b:
        return "BULL"
    if b > u:
        return "BEAR"
    if h.kind in ("geo",):
        return "BEAR"
    return "MIXED"


def classify_move(symbol: str, q: Quote, snap: Snapshot, session: Session) -> Verdict:
    meta = WATCH.get(symbol, {"beta_qqq": 1.0, "crypto_beta": 0.2})
    h = _best_headline(symbol, snap.headlines)
    news_dir = _direction_from_headline(h)
    hours_open = hours_to_next_cash_open()
    move = q.change_pct
    abs_move = abs(move)

    expected_qqq = snap.qqq_change_pct * meta["beta_qqq"]
    residual = move - expected_qqq
    crypto_pull = abs(snap.btc_change_pct) >= 0.6 and abs(move) >= 0.35 and (
        (move > 0 and snap.btc_change_pct > 0) or (move < 0 and snap.btc_change_pct < 0)
    )
    thin = q.volume_ratio < 0.55 or session.liquidity in ("thin", "vacuum")
    has_catalyst = h is not None and h.kind != "unknown"

    gates = {
        "cash_closed": not session.cash_open,
        "has_catalyst": has_catalyst,
        "volume_ok": q.volume_ratio >= 0.45,
        "not_just_btc": not (crypto_pull and not has_catalyst),
        "move_exists": abs_move >= 0.35,
        "not_open_trap": not (session.monday_gap_risk and hours_open <= 6),
        "residual_real": abs(residual) >= 0.25 or session.cash_open,
    }

    # Default
    regime = "DISCOVERY" if session.cash_open else "TAPE_NOISE"
    side = "NO_TRADE"
    reason = "No split-clock disagreement worth paying for."
    contra = "Any fresh opposing headline or a cash-open gap against the ticket."
    conf = 0.25
    size = 0.0

    if session.cash_open:
        regime = "DISCOVERY"
        reason = "Cash hours. Calder does not invent edge in the primary tape without a catalyst."
        if has_catalyst and abs_move >= 0.6 and news_dir in ("BULL", "BEAR"):
            side = "BUY" if news_dir == "BULL" else "SELL"
            conf = 0.52
            size = 0.35
            reason = f"Cash-hours catalyst ({h.kind}): {h.title[:110]}"
    elif crypto_pull and not has_catalyst:
        regime = "CRYPTO_BLEED"
        reason = (
            f"{symbol} is tracking BTC ({snap.btc_change_pct:+.2f}%) more than its own story. "
            "That is crypto beta dressed as equity. Do not buy the costume."
        )
        conf = 0.4
    elif session.monday_gap_risk and hours_open <= 8:
        regime = "OPEN_TRAP"
        reason = (
            f"{hours_open:.1f}h to cash open. Weekend/Friday night prints often unwind at 09:30. "
            "Calder stands down unless a true catalyst is still live."
        )
        conf = 0.45
        if has_catalyst and abs_move >= 0.8 and gates["not_just_btc"]:
            # still allow a reduced probe
            side = "BUY" if move > 0 and news_dir != "BEAR" else "SELL" if move < 0 and news_dir != "BULL" else "NO_TRADE"
            if side != "NO_TRADE":
                size = 0.25
                conf = 0.48
                reason = f"Open-trap window, but catalyst still live: {h.title[:110]}"
    elif has_catalyst and abs_move >= 0.4:
        aligned = (
            (news_dir == "BULL" and move > 0)
            or (news_dir == "BEAR" and move < 0)
            or news_dir == "MIXED"
        )
        if aligned and (not thin or abs_move >= 0.9):
            regime = "INFO_PRICE"
            side = "BUY" if move > 0 else "SELL"
            conf = 0.58 if not thin else 0.5
            size = 0.55 if session.liquidity != "vacuum" else 0.3
            reason = (
                f"Cash is closed. {symbol} moved {move:+.2f}% with a live {h.kind} headline "
                f"and residual {residual:+.2f}% vs QQQ. This is the 7x24 job."
            )
        else:
            regime = "TAPE_NOISE"
            reason = (
                f"Headline and tape disagree, or book is too thin (vol ratio {q.volume_ratio:.2f}). Fade temptation."
            )
    else:
        regime = "TAPE_NOISE" if not session.cash_open else "DISCOVERY"
        reason = f"{symbol} {move:+.2f}% with no usable catalyst in this session ({session.code})."

    # Hard vetoes
    if side != "NO_TRADE" and not gates["not_open_trap"] and size > 0.25:
        size = 0.25
    if side != "NO_TRADE" and not gates["not_just_btc"]:
        side, size, regime = "NO_TRADE", 0.0, "CRYPTO_BLEED"
        reason = "Veto: move is crypto-bleed without an equity catalyst."

    expire = session.default_hold_hours
    if regime == "INFO_PRICE":
        expire = min(session.default_hold_hours, max(3.0, hours_open - 0.5))

    return Verdict(
        symbol=symbol,
        side=side,
        regime=regime,
        confidence=round(conf, 3),
        size_pct=round(size, 3),
        reason=reason,
        contra=contra,
        expire_hours=round(expire, 2),
        gates=gates,
        headline=(h.title if h else ""),
    )


def scan(snap: Snapshot, session: Session, symbols: list[str]) -> list[Verdict]:
    out = []
    for s in symbols:
        q = snap.quotes.get(s)
        if not q:
            continue
        out.append(classify_move(s, q, snap, session))
    out.sort(key=lambda v: (v.side != "NO_TRADE", v.confidence), reverse=True)
    return out


def verdict_dict(v: Verdict) -> dict[str, Any]:
    return asdict(v)
from clock import Session, hours_to_next_cash_open
from data import Headline, Quote, Snapshot, WATCH
