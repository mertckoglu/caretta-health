from datetime import date, datetime, timedelta

import pandas as pd

from app.core.indicators import INDICATORS
from app.core.simulate import DEFAULT_EVENTS, simulate_crew, simulate_mission
from app.core.status import daily_table, detect_trends
from app.core.thresholds import RED, classify


def test_shape_and_validity():
    df = simulate_mission(days=30, start=date(2026, 1, 1))
    assert len(df) == 30 * len(INDICATORS)
    assert set(df.columns) == {"ts", "astronaut_id", "environment", "indicator", "value"}
    for row in df.itertuples():
        ind = INDICATORS[row.indicator]
        assert ind.min_valid <= row.value <= ind.max_valid
    assert df["ts"].min().date() == date(2026, 1, 1)


def test_deterministic_with_seed():
    a = simulate_mission(days=10, seed=7, start=date(2026, 1, 1))
    b = simulate_mission(days=10, seed=7, start=date(2026, 1, 1))
    c = simulate_mission(days=10, seed=8, start=date(2026, 1, 1))
    pd.testing.assert_frame_equal(a, b)
    assert not a["value"].equals(c["value"])


def test_default_ends_yesterday():
    df = simulate_mission(days=5)
    assert df["ts"].max().date() == date.today() - timedelta(days=1)


def test_scripted_events_are_visible():
    df = simulate_mission(days=30, start=date(2026, 1, 1))
    t = daily_table(df)
    spe = t["radiation_dose"].iloc[DEFAULT_EVENTS["spe_day"]]
    assert classify("radiation_dose", spe) == RED
    fever = t["body_temp"].iloc[DEFAULT_EVENTS["fever_days"][0]]
    assert fever >= 37.8
    assert t["exercise_minutes"].iloc[list(DEFAULT_EVENTS["missed_exercise_days"])].max() < 30


def test_no_events_is_mostly_healthy():
    df = simulate_mission(days=10, start=date(2026, 1, 1), events={})
    t = daily_table(df)
    assert classify("radiation_dose", t["radiation_dose"].max()) != RED
    assert t["body_temp"].max() < 37.8


def test_environment_changes_dose():
    iss = daily_table(simulate_mission(days=10, environment="iss", events={}))["radiation_dose"].mean()
    transit = daily_table(simulate_mission(days=10, environment="transit", events={}))["radiation_dose"].mean()
    assert transit > 2 * iss


def test_crew_and_trends_run():
    crew = simulate_crew(days=14)
    assert crew["astronaut_id"].nunique() == 4
    cdr = crew[crew["astronaut_id"] == "CDR"]
    assert isinstance(detect_trends(cdr), list)


def test_environment_changes_exercise_routine_and_status():
    rover = simulate_mission(days=10, environment="rover", events={}, start=date(2026, 1, 1))
    ex = daily_table(rover)["exercise_minutes"].mean()
    assert ex < 70
    assert classify("exercise_minutes", ex, "rover") != classify("exercise_minutes", ex, "iss")


def test_each_environment_has_its_own_scenario():
    from app.core.simulate import ENV_PROFILES
    from app.core.thresholds import ENVIRONMENTS

    assert set(ENV_PROFILES) == set(ENVIRONMENTS)
    start = date(2026, 1, 1)
    t = {e: daily_table(simulate_crew(days=30, environment=e, start=start).query("astronaut_id == 'CDR'"))
         for e in ENVIRONMENTS}
    # deep space: biggest solar particle event (no magnetosphere)
    assert t["transit"]["radiation_dose"].iloc[12] > t["iss"]["radiation_dose"].iloc[12] + 5
    # Mars: atmosphere shields the SPE
    assert t["mars_base"]["radiation_dose"].iloc[12] < t["iss"]["radiation_dose"].iloc[12]
    # Moon: regolith dust lowers SpO₂ after EVAs
    assert t["lunar_base"]["spo2"].iloc[8:10].mean() < t["lunar_base"]["spo2"].iloc[2:7].mean() - 2
    # Mars dust storm limits exercise
    assert t["mars_base"]["exercise_minutes"].iloc[10:15].mean() < 40
    # rover: cabin CO₂ build-up
    assert t["rover"]["spo2"].iloc[18:20].mean() < t["rover"]["spo2"].iloc[2:10].mean() - 2
    # datasets differ between environments
    assert not t["iss"]["heart_rate"].equals(t["mars_base"]["heart_rate"])


def test_practice_data_is_daily_and_leaves_today_free():
    # one report per day at midnight, ending yesterday: today belongs to the real check-in
    df = simulate_mission(days=3)
    assert (df["ts"].dt.date < date.today()).all()
    assert (df["ts"].dt.time == datetime.min.time()).all()
    assert not df.duplicated(["ts", "indicator"]).any()
