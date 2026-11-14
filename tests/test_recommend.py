from app.core.recommend import needs_escalation, recommend
from app.core.status import Level, evaluate_all


def test_all_normal_returns_single_normal_recommendation():
    recs = recommend(evaluate_all({"heart_rate": 70, "spo2": 98}))
    assert len(recs) == 1
    assert recs[0].level == Level.NORMAL
    assert not needs_escalation(recs)


def test_empty_status_is_normal():
    recs = recommend(evaluate_all({}))
    assert recs[0].level == Level.NORMAL


def test_single_watch_metric_gives_advice_without_escalation():
    recs = recommend(evaluate_all({"sleep_hours": 6.0}))
    assert len(recs) == 1
    assert recs[0].category == "behavioral"
    assert not needs_escalation(recs)


def test_warning_triggers_escalation():
    recs = recommend(evaluate_all({"spo2": 91}))
    assert needs_escalation(recs)


def test_critical_adds_flight_surgeon_message():
    recs = recommend(evaluate_all({"heart_rate": 150}))
    assert recs[0].level == Level.CRITICAL
    assert any("flight surgeon" in r.message for r in recs)
    assert needs_escalation(recs)


def test_sorted_most_severe_first():
    recs = recommend(evaluate_all({"sleep_hours": 6.0, "spo2": 85, "stress": 6}))
    levels = [r.level for r in recs]
    assert levels == sorted(levels, reverse=True)


def test_fever_and_high_heart_rate_combined_rule():
    recs = recommend(evaluate_all({"body_temp": 38.0, "heart_rate": 105}))
    assert any("possible infection" in r.message for r in recs)
    assert needs_escalation(recs)


def test_sleep_and_stress_combined_rule():
    recs = recommend(evaluate_all({"sleep_hours": 5.0, "stress": 7}))
    assert any("burnout" in r.message for r in recs)


def test_no_combined_rule_when_only_one_condition():
    recs = recommend(evaluate_all({"body_temp": 38.0}))
    assert not any("possible infection" in r.message for r in recs)


def test_low_vs_high_direction_gives_different_advice():
    high = recommend(evaluate_all({"heart_rate": 110}))[0].message
    low = recommend(evaluate_all({"heart_rate": 42}))[0].message
    assert high != low