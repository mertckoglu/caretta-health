import pytest

from app.core.status import Level, evaluate_all, evaluate_metric


@pytest.mark.parametrize(
    "name,value,level",
    [
        ("heart_rate", 70, Level.NORMAL),
        ("heart_rate", 95, Level.WATCH),
        ("heart_rate", 110, Level.WARNING),
        ("heart_rate", 150, Level.CRITICAL),
        ("heart_rate", 30, Level.CRITICAL),
        ("spo2", 98, Level.NORMAL),
        ("spo2", 94, Level.WATCH),
        ("spo2", 91, Level.WARNING),
        ("spo2", 85, Level.CRITICAL),
        ("body_temp", 36.6, Level.NORMAL),
        ("body_temp", 38.0, Level.WARNING),
        ("body_temp", 39.5, Level.CRITICAL),
        ("stress", 2, Level.NORMAL),
        ("stress", 9, Level.CRITICAL),
        ("daily_radiation_msv", 0.5, Level.NORMAL),
        ("daily_radiation_msv", 5.0, Level.CRITICAL),
    ],
)
def test_evaluate_metric_levels(name, value, level):
    assert evaluate_metric(name, value).level == level


def test_boundaries_are_inclusive():
    assert evaluate_metric("heart_rate", 90).level == Level.NORMAL
    assert evaluate_metric("heart_rate", 50).level == Level.NORMAL
    assert evaluate_metric("heart_rate", 100).level == Level.WATCH


def test_direction():
    assert evaluate_metric("heart_rate", 120).direction == "high"
    assert evaluate_metric("heart_rate", 42).direction == "low"
    assert evaluate_metric("heart_rate", 70).direction is None


def test_category_assigned():
    assert evaluate_metric("body_temp", 36.5).category == "immune"
    assert evaluate_metric("sleep_hours", 8).category == "behavioral"


def test_unknown_metric_raises():
    with pytest.raises(KeyError):
        evaluate_metric("not_a_metric", 1)


@pytest.mark.parametrize("bad", [None, float("nan")])
def test_invalid_value_raises(bad):
    with pytest.raises(ValueError):
        evaluate_metric("heart_rate", bad)


def test_evaluate_all_overall_is_worst():
    status = evaluate_all({"heart_rate": 70, "spo2": 85, "stress": 3})
    assert status.overall == Level.CRITICAL


def test_evaluate_all_all_normal():
    status = evaluate_all({"heart_rate": 70, "spo2": 98, "sleep_hours": 8})
    assert status.overall == Level.NORMAL
    assert status.abnormal() == []


def test_evaluate_all_unknown_and_none_handled():
    status = evaluate_all({"heart_rate": 70, "foo": 1, "spo2": None})
    assert status.unknown == ["foo"]
    assert "spo2" not in status.metrics


def test_empty_readings_is_normal():
    assert evaluate_all({}).overall == Level.NORMAL


def test_by_category_and_abnormal_ordering():
    status = evaluate_all({"heart_rate": 150, "body_temp": 37.7, "mood": 4})
    cats = status.by_category()
    assert cats["cardiovascular"] == Level.CRITICAL
    assert cats["immune"] == Level.WATCH
    assert cats["behavioral"] == Level.NORMAL
    assert [m.name for m in status.abnormal()] == ["heart_rate", "body_temp"]