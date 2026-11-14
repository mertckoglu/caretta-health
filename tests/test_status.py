from datetime import datetime, timedelta

import pandas as pd
import pytest

from app.core.status import (
    daily_table,
    detect_trends,
    evaluate_latest,
    evaluate_snapshot,
    needs_flight_surgeon,
    overall_status,
    region_status,
)
from app.core.thresholds import GREEN, RED, UNKNOWN, YELLOW, classify, direction, get_thresholds, worst


@pytest.mark.parametrize(
    "indicator,value,expected",
    [
        ("heart_rate", 65, GREEN),
        ("heart_rate", 45, YELLOW),
        ("heart_rate", 110, YELLOW),
        ("heart_rate", 130, RED),
        ("heart_rate", 35, RED),
        ("systolic_bp", 129, GREEN),
        ("systolic_bp", 130, YELLOW),  # bands are half-open
        ("systolic_bp", 165, RED),
        ("spo2", 99, GREEN),
        ("spo2", 93, YELLOW),
        ("spo2", 88, RED),
        ("body_temp", 36.8, GREEN),
        ("body_temp", 37.7, YELLOW),
        ("body_temp", 38.6, RED),
        ("blood_glucose", 50, RED),
        ("blood_glucose", 60, YELLOW),
        ("sleep_hours", 4, RED),
        ("mood", 5, GREEN),
        ("mood", 3, YELLOW),
        ("mood", 1, RED),
        ("radiation_dose", 0.4, GREEN),
        ("radiation_dose", 8, RED),
    ],
)
def test_classify(indicator, value, expected):
    assert classify(indicator, value) == expected


def test_classify_missing_is_unknown():
    assert classify("heart_rate", None) == UNKNOWN
    assert classify("heart_rate", float("nan")) == UNKNOWN


def test_environment_override_changes_radiation_band():
    assert classify("radiation_dose", 1.8, "iss") == YELLOW
    assert classify("radiation_dose", 1.8, "transit") == GREEN
    # base table must not be mutated by overrides
    assert get_thresholds("radiation_dose", "iss")["green"] == [(0, 1.0)]


def test_unknown_indicator_raises():
    with pytest.raises(KeyError):
        classify("cholesterol", 100)


def test_direction():
    assert direction("heart_rate", 40) == "low"
    assert direction("heart_rate", 130) == "high"
    assert direction("heart_rate", 70) == "ok"


def test_worst():
    assert worst([GREEN, YELLOW, UNKNOWN]) == YELLOW
    assert worst([GREEN, RED, YELLOW]) == RED
    assert worst([]) == UNKNOWN
    assert worst([UNKNOWN, UNKNOWN]) == UNKNOWN


def test_snapshot_and_regions():
    statuses = evaluate_snapshot({"heart_rate": 130, "spo2": 98, "mood": 3})
    assert statuses["heart_rate"].status == RED
    assert statuses["blood_glucose"].status == UNKNOWN
    regions = region_status(statuses)
    assert regions["heart"] == RED
    assert regions["lungs"] == GREEN
    assert regions["brain"] == YELLOW
    assert regions["metabolism"] == UNKNOWN
    assert overall_status(statuses) == RED


def test_escalation():
    esc, reasons = needs_flight_surgeon(evaluate_snapshot({"spo2": 85}))
    assert esc and "Oxygen" in reasons[0]
    esc, _ = needs_flight_surgeon(evaluate_snapshot({"heart_rate": 70, "spo2": 98}))
    assert not esc
    esc, reasons = needs_flight_surgeon(evaluate_snapshot({"heart_rate": 110, "spo2": 93, "mood": 3}))
    assert esc and "yellow" in reasons[0]


def _series(indicator, values, start=None):
    start = start or datetime(2026, 1, 1, 7)
    return pd.DataFrame(
        {"ts": [start + timedelta(days=i) for i in range(len(values))], "indicator": indicator, "value": values}
    )


def test_latest_takes_most_recent():
    df = pd.concat([_series("heart_rate", [60, 61, 125])])
    st = evaluate_latest(df)
    assert st["heart_rate"].value == 125
    assert st["heart_rate"].status == RED
    assert st["heart_rate"].ts.startswith("2026-01-03")


def test_daily_table_shape():
    df = pd.concat([_series("heart_rate", [60, 62]), _series("mood", [4, 5])])
    t = daily_table(df)
    assert len(t) == 2 and t.loc[t.index[0], "heart_rate"] == 60


def test_trend_sleep_debt_and_persistence():
    df = _series("sleep_hours", [7.5, 7, 5.2, 5.0, 5.1, 5.3, 5.0])
    alerts = detect_trends(df)
    titles = " | ".join(a.title for a in alerts)
    assert "Sleep debt" in titles
    assert "days in a row" in titles


def test_trend_heart_rate_drift():
    df = _series("heart_rate", [60] * 7 + [62, 63, 72, 74, 75])
    alerts = detect_trends(df)
    assert any(a.indicator == "heart_rate" and "baseline" in a.title for a in alerts)


def test_trend_cumulative_dose():
    df = _series("radiation_dose", [0.5] * 10)
    assert not [a for a in detect_trends(df) if a.indicator == "radiation_dose"]
    alerts = detect_trends(df, prior_career_dose_msv=500)
    dose = [a for a in alerts if a.indicator == "radiation_dose"]
    assert dose and dose[0].status == RED


def test_no_data_no_alerts():
    assert detect_trends(pd.DataFrame(columns=["ts", "indicator", "value"])) == []
