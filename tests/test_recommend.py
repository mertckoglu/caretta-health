from datetime import date, datetime, timedelta

import pandas as pd

from app.core.indicators import CORE_INDICATORS, INDICATORS
from app.core.recommend import (
    CMO,
    GUIDANCE,
    SELF,
    SURGEON,
    badges,
    downlink_report,
    level_for,
    recommend,
    recommendations_for,
    streak_days,
    task_progress,
    xp_total,
)
from app.core.status import detect_trends, evaluate_snapshot
from app.core.thresholds import GREEN, RED, UNKNOWN, YELLOW, classify


def test_red_recommendation_escalates_to_surgeon():
    r = recommend("heart_rate", 135, RED)
    assert r.escalate and r.contact == SURGEON
    assert "high" in r.title and r.actions


def test_yellow_low_glucose_gives_carbohydrate_advice():
    r = recommend("blood_glucose", 62, YELLOW)
    assert r.contact == SELF
    assert any("carbohydrate" in a for a in r.actions)


def test_yellow_spo2_goes_to_cmo():
    assert recommend("spo2", 93, YELLOW).contact == CMO


def test_green_and_unknown():
    assert recommend("mood", 5, GREEN).status == GREEN
    r = recommend("mood", None, UNKNOWN)
    assert r.status == UNKNOWN and "How to measure" in r.actions[0]


def test_every_non_green_case_has_specific_guidance():
    """Each indicator must have advice for every direction it can go out of range."""
    for key in INDICATORS:
        for value in (INDICATORS[key].min_valid, INDICATORS[key].max_valid):
            status = classify(key, value)
            if status in (YELLOW, RED):
                r = recommend(key, value, status)
                assert r.actions and "Re-measure and inform" not in r.actions[0], (key, value)
    assert set(GUIDANCE) == set(INDICATORS)


def test_recommendations_sorted_by_severity():
    statuses = evaluate_snapshot({"heart_rate": 110, "spo2": 85, "mood": 5})
    recs = recommendations_for(statuses)
    assert [r.status for r in recs] == [RED, YELLOW]
    assert len(recommendations_for(statuses, include_green=True)) == 3


def _complete_day(day):
    ts = datetime.combine(day, datetime.min.time()) + timedelta(hours=8)
    return pd.DataFrame({"ts": ts, "indicator": CORE_INDICATORS, "value": [INDICATORS[k].default for k in CORE_INDICATORS]})


def test_streak_and_xp():
    today = date(2026, 3, 10)
    df = pd.concat([_complete_day(today - timedelta(days=i)) for i in range(4)])
    assert streak_days(df, today) == 4
    # yesterday-ending streak still counts if today not done yet
    assert streak_days(df, today + timedelta(days=1)) == 4
    assert streak_days(df, today + timedelta(days=3)) == 0
    assert xp_total(df) > 4 * 25
    earned = {b["name"] for b in badges(df, today) if b["earned"]}
    assert {"First Contact", "Orbit Keeper"} <= earned
    assert "Week in Space" not in earned


def test_level_progression():
    assert level_for(0)["name"] == "Cadet"
    lv = level_for(400)
    assert lv["name"] == "Flight Engineer" and lv["next_name"] == "Mission Specialist"
    assert 0 < lv["progress"] < 1
    assert level_for(10_000)["next_name"] is None


def test_task_progress_states():
    day = date(2026, 3, 10)
    df = pd.DataFrame({"ts": [datetime(2026, 3, 10, 7)], "indicator": ["blood_glucose"], "value": [90]})
    tasks = {t["id"]: t["state"] for t in task_progress(df, day, now=datetime(2026, 3, 10, 9))}
    assert tasks["fasting_glucose"] == "done"
    assert tasks["morning_vitals"] == "due"
    assert tasks["evening_checkin"] == "upcoming"


def test_downlink_report_contains_table_and_escalation():
    statuses = evaluate_snapshot({"heart_rate": 130, "spo2": 98})
    df = pd.DataFrame({"ts": [datetime(2026, 1, 1)], "indicator": ["heart_rate"], "value": [130]})
    alerts = detect_trends(df)
    md = downlink_report("CDR", "iss", statuses, alerts, recommendations_for(statuses, alerts), 12.3)
    assert "# Caretta health downlink — CDR" in md
    assert "flight surgeon review requested" in md
    assert "| Resting heart rate | 130 bpm |" in md
    assert "12.3 mSv" in md


def test_autonomy_note_depends_on_comm_delay():
    from app.core.recommend import autonomy_note

    statuses = evaluate_snapshot({"spo2": 85})
    iss = recommendations_for(statuses, environment="iss")
    mars = recommendations_for(statuses, environment="mars_base")
    assert autonomy_note("iss") is None and autonomy_note("lunar_base") is None
    assert not any("Communication delay" in a for a in iss[0].actions)
    assert any("Communication delay" in a for a in mars[0].actions)
