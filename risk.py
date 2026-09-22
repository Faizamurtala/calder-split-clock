"""Risk cage. The model never sizes a ticket. This file does."""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class RiskConfig:
    equity: float = 10_000.0
    risk_pct: float = 0.75          # % of equity risked per ticket
    max_positions: int = 3
    max_gross_pct: float = 2.4      # 3 * 0.75
    stop_pct: float = 1.6
    take_pct: float = 2.4
    max_leverage: float = 1.0       # paper spot-style, no leverage games
    weekend_size_mult: float = 0.55
    vacuum_size_mult: float = 0.45


@dataclass
class Ticket:
    symbol: str
    side: str
    qty_usd: float
    stop_pct: float
    take_pct: float
    expire_hours: float
    regime: str
    reason: str
    contra: str
    confidence: float
    accepted: bool
    reject_reason: str


def build_ticket(
    *,
    symbol: str,
    side: str,
    size_pct_hint: float,
    regime: str,
    confidence: float,
    expire_hours: float,
    reason: str,
    contra: str,
    session_code: str,
    liquidity: str,
    open_positions: int,
    cfg: RiskConfig,
) -> Ticket:
    reject = ""
    if side == "NO_TRADE":
        reject = "Signal said stand down."
    elif open_positions >= cfg.max_positions:
        reject = f"Book full ({open_positions}/{cfg.max_positions})."
    elif confidence < 0.48:
        reject = "Confidence below 0.48 cage."
    elif regime in ("TAPE_NOISE", "CRYPTO_BLEED") and side != "NO_TRADE":
        reject = f"Regime {regime} is not tradable."

    mult = 1.0
    if session_code == "WEEKEND":
        mult *= cfg.weekend_size_mult
    if liquidity == "vacuum":
        mult *= cfg.vacuum_size_mult
    if regime == "OPEN_TRAP":
        mult *= 0.5

    risk_usd = cfg.equity * (cfg.risk_pct / 100.0) * max(size_pct_hint, 0.25) * mult
    # Convert risk-at-stop into notional
    notional = risk_usd / (cfg.stop_pct / 100.0) if cfg.stop_pct else 0.0
    notional = min(notional, cfg.equity * 0.20)

    accepted = reject == "" and side in ("BUY", "SELL") and notional >= 25
    if not accepted and not reject:
        reject = "Notional too small after session haircut."

    return Ticket(
        symbol=symbol,
        side=side if accepted else "NO_TRADE",
        qty_usd=round(notional if accepted else 0.0, 2),
        stop_pct=cfg.stop_pct,
        take_pct=cfg.take_pct,
        expire_hours=expire_hours,
        regime=regime,
        reason=reason,
        contra=contra,
        confidence=confidence,
        accepted=accepted,
        reject_reason=reject,
    )


def ticket_dict(t: Ticket) -> dict:
    return asdict(t)
