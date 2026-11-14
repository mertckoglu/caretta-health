"""Turn raw readings into statuses, body-region statuses and trend alerts.

Readings are handled as a *long* pandas DataFrame with at least the columns
``ts`` (datetime), ``indicator`` (str) and ``value`` (float).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from app.core.indicators import INDICATORS, REGIONS
from app.core.thresholds import (
    CAREER_DOSE_LIMIT_MSV,
    DEFAULT_ENVIRONMENT,
    GREEN,
    RED,
    SEVERITY,
    UNKNOWN,
    YELLOW,
    classify,
    worst,
)

READING_COLUMNS = ["ts", "indicator", "value"]


@dataclass
class IndicatorStatus:
    indicator: str
    value: float | None
    status: str
    ts: str | None = None

    @property
    def name(self) -> str:
        return INDICATORS[self.indicator].name

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TrendAlert:
    indicator: str
    status: str
    title: str          # precise, clinical wording (reports for the medical team)
    message: str
    kind: str = ""      # persistent | sleep_debt | hr_drift | low_mood | dose — used for crew-facing wording
    value: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- snapshot --
def normalize(df: pd.DataFrame | None) -> pd.DataFrame:
    """Return a clean copy with typed columns, sorted by time."""
    if df is None or df.empty:
        return pd.DataFrame(columns=READING_COLUMNS)
    out = df.copy()
    out["ts"] = pd.to_datetime(out["ts"])
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out[out["indicator"].isin(INDICATORS)]
    return out.sort_values("ts").reset_index(drop=True)


def latest_values(df: pd.DataFrame) -> dict[str, tuple[float, pd.Timestamp]]:
    """Most recent value (and its timestamp) for every indicator."""
    df = normalize(df)
    result: dict[str, tuple[float, pd.Timestamp]] = {}
    if df.empty:
        return result
    last = df.groupby("indicator").tail(1)
    for row in last.itertuples():
        result[row.indicator] = (float(row.value), row.ts)
    return result


def evaluate_snapshot(
    values: dict[str, float | None], environment: str = DEFAULT_ENVIRONMENT
) -> dict[str, IndicatorStatus]:
    """Classify a dict of ``indicator -> value``. Missing indicators are ``unknown``."""
    out = {}
    for key in INDICATORS:
        v = values.get(key)
        out[key] = IndicatorStatus(key, None if v is None else float(v), classify(key, v, environment))
    return out


def evaluate_latest(df: pd.DataFrame, environment: str = DEFAULT_ENVIRONMENT) -> dict[str, IndicatorStatus]:
    latest = latest_values(df)
    statuses = evaluate_snapshot({k: v for k, (v, _) in latest.items()}, environment)
    for k, (_, ts) in latest.items():
        statuses[k].ts = pd.Timestamp(ts).isoformat()
    return statuses


def overall_status(statuses: dict[str, IndicatorStatus], alerts: list[TrendAlert] | None = None) -> str:
    items = [s.status for s in statuses.values()]
    items += [a.status for a in alerts or []]
    return worst(items)


def region_status(
    statuses: dict[str, IndicatorStatus], alerts: list[TrendAlert] | None = None
) -> dict[str, str]:
    """Worst status per body region (trend alerts included)."""
    alert_by_ind: dict[str, list[str]] = {}
    for a in alerts or []:
        alert_by_ind.setdefault(a.indicator, []).append(a.status)
    out = {}
    for region, meta in REGIONS.items():
        st = [statuses[k].status for k in meta["indicators"] if k in statuses]
        for k in meta["indicators"]:
            st += alert_by_ind.get(k, [])
        out[region] = worst(st)
    return out


# ------------------------------------------------------------------ trends --
def daily_table(df: pd.DataFrame) -> pd.DataFrame:
    """Daily mean of each indicator (index = date, columns = indicators)."""
    df = normalize(df)
    if df.empty:
        return pd.DataFrame(columns=list(INDICATORS))
    df = df.assign(date=df["ts"].dt.normalize())
    table = df.pivot_table(index="date", columns="indicator", values="value", aggfunc="mean")
    return table.reindex(columns=list(INDICATORS))


def daily_status_table(df: pd.DataFrame, environment: str = DEFAULT_ENVIRONMENT) -> pd.DataFrame:
    """Same shape as :func:`daily_table`, filled with status strings."""
    table = daily_table(df)
    return table.apply(lambda col: col.map(lambda v: classify(col.name, v, environment)))


def _consecutive_non_green(statuses: pd.Series) -> int:
    count = 0
    for s in reversed(statuses.dropna().tolist()):
        if s in (YELLOW, RED):
            count += 1
        elif s == UNKNOWN:
            continue
        else:
            break
    return count


def detect_trends(
    df: pd.DataFrame,
    environment: str = DEFAULT_ENVIRONMENT,
    prior_career_dose_msv: float = 0.0,
) -> list[TrendAlert]:
    """Rules that look at several days instead of a single reading."""
    table = daily_table(df)
    alerts: list[TrendAlert] = []
    if table.empty:
        return alerts
    status_table = daily_status_table(df, environment)

    # 1. Persistent out-of-range values (3+ days in a row → yellow, 7+ → red)
    for ind in INDICATORS:
        if ind not in status_table:
            continue
        n = _consecutive_non_green(status_table[ind][status_table[ind] != UNKNOWN])
        if n >= 3:
            alerts.append(
                TrendAlert(
                    ind,
                    RED if n >= 7 else YELLOW,
                    f"{INDICATORS[ind].name}: out of range {n} days in a row",
                    "A persistent deviation is more meaningful than a single reading. "
                    "Review the guidance and discuss it at the next medical conference.",
                    "persistent",
                    n,
                )
            )

    # 2. Sleep debt (7-day average)
    sleep = table["sleep_hours"].dropna().tail(7)
    if len(sleep) >= 3:
        avg = sleep.mean()
        if avg < 6.0:
            alerts.append(
                TrendAlert(
                    "sleep_hours",
                    RED if avg < 5.0 else YELLOW,
                    f"Sleep debt: {avg:.1f} h/night average over {len(sleep)} days",
                    "Chronic short sleep degrades attention and mood. Protect the sleep period, "
                    "use eye mask/earplugs and ask the crew to review the schedule.",
                    "sleep_debt",
                    float(avg),
                )
            )

    # 3. Resting heart rate drift vs. personal baseline (first 7 days)
    hr = table["heart_rate"].dropna()
    if len(hr) >= 10:
        baseline = hr.head(7).mean()
        recent = hr.tail(3).mean()
        if recent > baseline * 1.15:
            alerts.append(
                TrendAlert(
                    "heart_rate",
                    YELLOW,
                    f"Resting heart rate up {100 * (recent / baseline - 1):.0f}% vs. your baseline",
                    f"Baseline {baseline:.0f} bpm, last 3 days {recent:.0f} bpm. Check hydration, "
                    "temperature, sleep and training load.",
                    "hr_drift",
                    float(100 * (recent / baseline - 1)),
                )
            )

    # 4. Low mood trend
    mood = table["mood"].dropna().tail(3)
    if len(mood) >= 3 and mood.mean() <= 2.5:
        alerts.append(
            TrendAlert(
                "mood",
                YELLOW,
                f"Low mood for several days (average {mood.mean():.1f}/5)",
                "Consider a private conference with the behavioural health team and a call with "
                "family. You are not alone in this.",
                "low_mood",
                float(mood.mean()),
            )
        )

    # 5. Cumulative radiation dose vs. career limit
    dose = table["radiation_dose"].dropna().sum() + prior_career_dose_msv
    frac = dose / CAREER_DOSE_LIMIT_MSV
    if frac >= 0.5:
        alerts.append(
            TrendAlert(
                "radiation_dose",
                RED if frac >= 0.8 else YELLOW,
                f"Cumulative dose {dose:.0f} mSv ({100 * frac:.0f}% of career limit)",
                "Flight surgeons and radiation health officers should review exposure planning.",
                "dose",
                float(dose),
            )
        )

    alerts.sort(key=lambda a: -SEVERITY[a.status])
    return alerts


def cumulative_dose(df: pd.DataFrame) -> float:
    table = daily_table(df)
    if table.empty or "radiation_dose" not in table:
        return 0.0
    return float(table["radiation_dose"].dropna().sum())


# ------------------------------------------------------------ escalation --
def needs_flight_surgeon(
    statuses: dict[str, IndicatorStatus], alerts: list[TrendAlert] | None = None
) -> tuple[bool, list[str]]:
    """Return (escalate?, reasons). Any red result or red trend escalates."""
    reasons = [
        f"{s.name}: {INDICATORS[s.indicator].format(s.value)} (red)"
        for s in statuses.values()
        if s.status == RED
    ]
    reasons += [a.title for a in alerts or [] if a.status == RED]
    yellow_count = sum(1 for s in statuses.values() if s.status == YELLOW)
    if yellow_count >= 3:
        reasons.append(f"{yellow_count} indicators in the yellow zone at the same time")
    return bool(reasons), reasons


def completeness(statuses: dict[str, IndicatorStatus]) -> float:
    known = sum(1 for s in statuses.values() if s.status != UNKNOWN)
    return known / len(statuses) if statuses else 0.0


__all__ = [
    "GREEN",
    "YELLOW",
    "RED",
    "UNKNOWN",
    "IndicatorStatus",
    "TrendAlert",
    "normalize",
    "latest_values",
    "evaluate_snapshot",
    "evaluate_latest",
    "overall_status",
    "region_status",
    "daily_table",
    "daily_status_table",
    "detect_trends",
    "cumulative_dose",
    "needs_flight_surgeon",
    "completeness",
]
