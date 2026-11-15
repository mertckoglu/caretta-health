from datetime import date, datetime, timedelta

import pandas as pd

from app.core.companion import (
    address,
    alert_text,
    care_reasons,
    day_summary,
    greeting,
    mission_patches,
    missed_checkin,
    overall,
    patch_progress_line,
)
from app.core.indicators import CORE_INDICATORS, INDICATORS
from app.core.status import TrendAlert, detect_trends, evaluate_snapshot
from app.core.thresholds import RED, STATUS_LABELS, status_hint, status_label

NOW = datetime(2026, 3, 10, 7, 30)


def _snap(values, ts=NOW):
    st = evaluate_snapshot(values)
    for k in values:
        st[k].ts = ts.isoformat()
    return st


def test_labels_split_red_into_needs_care_and_act_now():
    assert STATUS_LABELS == {"green": "Smooth sailing", "yellow": "Shifting tides", "red": "Act now",
                             "unknown": "No reading yet"}
    assert status_label(RED, "sleep_hours") == "Needs care"
    assert status_label(RED, "spo2") == "Act now"
    assert "not alone" in status_hint(RED, "mood")


def test_address_and_greeting_follow_role_and_time():
    assert address("CDR") == "Commander" and address("MS2") == "Mission Specialist" and address("Ayşe") == "Ayşe"
    assert greeting("CDR", NOW) == "Good morning, Commander."
    assert greeting("PLT", NOW.replace(hour=15)).startswith("Good afternoon, Pilot")
    assert greeting("PLT", NOW.replace(hour=20)).startswith("Good evening")


def test_day_summary_matches_the_example():
    st = _snap({"sleep_hours": 7.0, "heart_rate": 60})
    s = day_summary(st, now=NOW)
    assert s == "You slept 7 hours last night, and your resting heart rate is 60. You're starting the day well."


def test_day_summary_without_data_invites_instead_of_blaming():
    s = day_summary(evaluate_snapshot({}), now=NOW)
    assert "Whenever you're ready" in s


def test_overall_uses_needs_care_for_slow_problems_and_act_now_for_acute():
    assert overall(_snap({"sleep_hours": 4.5})).label == "Needs care"
    assert overall(_snap({"spo2": 88})).label == "Act now"
    assert overall(_snap({"heart_rate": 65})).label == "Smooth sailing"
    assert overall(_snap({"heart_rate": 110})).label == "Shifting tides"


def test_trend_alert_is_rephrased_without_rule_language():
    days = [NOW - timedelta(days=k) for k in range(7)][::-1]
    df = pd.DataFrame({"ts": days, "indicator": "sleep_hours", "value": [5.8] * 7})
    alerts = detect_trends(df)
    persistent = next(a for a in alerts if a.kind == "persistent")
    head, msg = alert_text(persistent)
    assert head == "You've slept below your target for 7 nights now"
    assert "flight surgeon" in msg and "out of range" not in head + msg
    assert "in a row" in persistent.title  # clinical wording kept for the medical report


def test_care_reasons_are_plain_language():
    st = _snap({"spo2": 88})
    r = care_reasons(st, [TrendAlert("sleep_hours", RED, "x", "y", "sleep_debt", 4.6)])
    assert r[0] == "your oxygen saturation (SpO₂) is low at 88 %"
    assert r[1].startswith("you've averaged 4.6 hours")


def test_missed_checkin_is_gentle():
    df = pd.DataFrame({"ts": [datetime(2026, 3, 8, 8)], "indicator": ["mood"], "value": [4]})
    assert missed_checkin(df, date(2026, 3, 10)) == "We missed you yesterday. Is everything okay?"
    assert "haven't heard from you in 2 days" in missed_checkin(df, date(2026, 3, 11))
    assert missed_checkin(df, date(2026, 3, 9)) is None
    assert missed_checkin(pd.DataFrame(columns=["ts", "indicator", "value"]), date(2026, 3, 9)) is None


def test_patches_only_add_up():
    rows = []
    for k in range(10):
        d = datetime(2026, 3, 1, 8) + timedelta(days=k)
        rows += [{"ts": d, "indicator": i, "value": INDICATORS[i].default} for i in CORE_INDICATORS]
    df = pd.DataFrame(rows)
    p = {x.id: x for x in mission_patches(df)}
    assert p["first_light"].earned and p["first_week"].earned
    assert not p["steady_hand"].earned and p["steady_hand"].to_go == 20
    # a gap afterwards takes nothing away
    later = pd.concat([df, pd.DataFrame([{"ts": datetime(2026, 4, 1, 8), "indicator": "mood", "value": 4}])])
    assert {x.id for x in mission_patches(later) if x.earned} >= {"first_light", "first_week"}
    assert "No rush" in patch_progress_line(p["steady_hand"])
    assert mission_patches(df, photos=1)[-1].earned
