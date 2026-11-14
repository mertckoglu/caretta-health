from datetime import date, datetime, timedelta

import pandas as pd

from app.core.indicators import CORE_INDICATORS, INDICATORS
from app.core.recommend import (
    CMO,
    DAILY_TASKS,
    GUIDANCE,
    SELF,
    SURGEON,
    downlink_report,
    recommend,
    recommendations_for,
    streak_days,
    weekly_review,
    task_progress,
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


def test_streak():
    today = date(2026, 3, 10)
    df = pd.concat([_complete_day(today - timedelta(days=i)) for i in range(4)])
    assert streak_days(df, today) == 4
    # a streak ending yesterday still counts if today isn't done yet
    assert streak_days(df, today + timedelta(days=1)) == 4
    assert streak_days(df, today + timedelta(days=3)) == 0


def _week(day, sleep, exercise, full=True):
    rows = []
    for k in range(7):
        d = datetime.combine(day - timedelta(days=k), datetime.min.time())
        inds = CORE_INDICATORS + ["radiation_dose"] if full else ["heart_rate"]
        for ind in inds:
            v = {"sleep_hours": sleep[k], "exercise_minutes": exercise[k]}.get(ind, INDICATORS[ind].default)
            rows.append({"ts": d + timedelta(hours=8), "indicator": ind, "value": v})
    return pd.DataFrame(rows)


def test_weekly_review_good_week():
    today = date(2026, 3, 10)
    df = _week(today, [7.5] * 7, [100] * 7)
    r = weekly_review(df, "iss", today=today, now=datetime(2026, 3, 10, 23))
    h = {x["id"]: x for x in r["habits"]}
    assert h["measurements"]["ratio"] == 1.0 and h["measurements"]["status"] == GREEN
    assert h["sleep"]["value"] == 7 and h["exercise"]["value"] == 7 and h["checkins"]["value"] == 7
    assert r["focus"] is None
    assert "xp" not in str(r).lower()


def test_weekly_review_points_at_the_weakest_habit():
    today = date(2026, 3, 10)
    df = _week(today, [5.5, 6, 6.5, 7.5, 5, 6, 6], [100] * 7)
    r = weekly_review(df, "iss", today=today, now=datetime(2026, 3, 10, 23))
    h = {x["id"]: x for x in r["habits"]}
    assert h["sleep"]["value"] == 1 and h["sleep"]["status"] == RED
    assert "Sleep" in r["focus"]


def test_weekly_review_uses_environment_exercise_target():
    today = date(2026, 3, 10)
    df = _week(today, [8] * 7, [45] * 7)
    iss = {x["id"]: x for x in weekly_review(df, "iss", today=today, now=datetime(2026, 3, 10, 23))["habits"]}
    rover = {x["id"]: x for x in weekly_review(df, "rover", today=today, now=datetime(2026, 3, 10, 23))["habits"]}
    assert iss["exercise"]["value"] == 0 and rover["exercise"]["value"] == 7
    assert "90" in iss["exercise"]["label"] and "30" in rover["exercise"]["label"]


def test_weekly_review_ignores_tasks_not_due_yet_and_compares_weeks():
    today = date(2026, 3, 10)
    df = _week(today, [8] * 7, [100] * 7, full=False)
    early = weekly_review(df, "iss", today=today, now=datetime(2026, 3, 10, 6))
    late = weekly_review(df, "iss", today=today, now=datetime(2026, 3, 10, 23))
    m_early = early["habits"][0]["target"]
    m_late = late["habits"][0]["target"]
    assert m_early == m_late - len(DAILY_TASKS)  # nothing is due at 6:00 today
    assert late["habits"][0]["status"] == RED and late["trend"] is None
    both = pd.concat([_week(today, [8] * 7, [100] * 7), _week(today - timedelta(days=7), [8] * 7, [100] * 7, full=False)])
    assert weekly_review(both, "iss", today=today, now=datetime(2026, 3, 10, 23))["trend"] == "better"


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
    assert "care team looped in" in md
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
