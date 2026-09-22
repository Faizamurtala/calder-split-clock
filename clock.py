"""Two clocks. That is the whole product.

Wall-Street clock = cash equity hours (price discovery).
Chain clock      = rToken 7x24 tape (can move when NY is dark).

A trade is only interesting when the two clocks disagree.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class Session:
    code: str
    label: str
    cash_open: bool
    liquidity: str  # rich | normal | thin | vacuum
    default_hold_hours: float
    monday_gap_risk: bool
    note: str


def now_ny(ts: datetime | None = None) -> datetime:
    if ts is None:
        return datetime.now(NY)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=NY)
    return ts.astimezone(NY)


def is_us_holiday_weekend(dt: datetime) -> bool:
    d = now_ny(dt)
    return d.weekday() >= 5


def classify_session(ts: datetime | None = None) -> Session:
    d = now_ny(ts)
    t = d.time()
    wd = d.weekday()  # Mon=0

    # Weekend vacuum — rToken still prints, cash does not
    if wd >= 5:
        return Session(
            code="WEEKEND",
            label="Weekend vacuum",
            cash_open=False,
            liquidity="vacuum",
            default_hold_hours=18,
            monday_gap_risk=True,
            note="Cash market is closed. Moves are information, crypto-beta bleed, or thin-book noise.",
        )

    # Regular cash session
    if time(9, 30) <= t < time(16, 0):
        return Session(
            code="CASH",
            label="US cash hours",
            cash_open=True,
            liquidity="rich",
            default_hold_hours=6,
            monday_gap_risk=False,
            note="Price discovery is on. Prefer confirmation over prediction.",
        )

    # Pre-market
    if time(4, 0) <= t < time(9, 30):
        return Session(
            code="PRE",
            label="US pre-market",
            cash_open=False,
            liquidity="thin",
            default_hold_hours=4,
            monday_gap_risk=False,
            note="Partial discovery. Size down. News can gap into the open.",
        )

    # After hours
    if time(16, 0) <= t < time(20, 0):
        return Session(
            code="AH",
            label="US after-hours",
            cash_open=False,
            liquidity="thin",
            default_hold_hours=8,
            monday_gap_risk=False,
            note="Earnings and guidance land here. Separate catalyst from tape noise.",
        )

    # Overnight / Asia hours on a weekday
    return Session(
        code="NIGHT",
        label="Overnight chain tape",
        cash_open=False,
        liquidity="vacuum" if wd == 4 and t >= time(20, 0) else "thin",
        default_hold_hours=10,
        monday_gap_risk=wd == 4,
        note="rToken is the only clock. Treat every print as unconfirmed until cash opens.",
    )


def hours_to_next_cash_open(ts: datetime | None = None) -> float:
    d = now_ny(ts)
    # walk forward to next weekday 09:30
    cursor = d
    for _ in range(8):
        open_dt = datetime.combine(cursor.date(), time(9, 30), tzinfo=NY)
        if cursor.weekday() < 5 and open_dt > d:
            return (open_dt - d).total_seconds() / 3600
        cursor = datetime.combine(cursor.date() + timedelta(days=1), time(0, 0), tzinfo=NY)
    return 48.0


def ticket_expiry(session: Session, ts: datetime | None = None) -> datetime:
    d = now_ny(ts)
    return d + timedelta(hours=session.default_hold_hours)
