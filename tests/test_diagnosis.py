import pytest

from app.core.diagnosis import (
    CMO,
    EMERGENCY,
    OUTCOMES,
    QUESTIONS,
    SELF,
    START,
    SURGEON,
    URGENCY,
    Outcome,
    Question,
    assess,
    max_depth,
    node,
    walk,
)
from app.core.indicators import HAZARDS, INDICATORS
from app.core.status import evaluate_snapshot


def _paths(nid="start", path=()):
    n = node(nid)
    if isinstance(n, Outcome):
        yield list(path), n
        return
    for i, opt in enumerate(n.options):
        yield from _paths(opt.next, path + (i,))


def test_tree_is_complete_and_acyclic():
    reached = set()
    for path, out in _paths():
        reached.add(out.id)
        assert len(path) <= 8
    assert reached == set(OUTCOMES), f"unreachable outcomes: {set(OUTCOMES) - reached}"
    used_questions = {o.next for q in QUESTIONS.values() for o in q.options} | {START}
    assert set(QUESTIONS) <= used_questions
    assert not set(QUESTIONS) & set(OUTCOMES)
    assert max_depth() <= 6


def test_outcome_content_is_valid():
    for o in OUTCOMES.values():
        assert o.urgency in URGENCY and o.actions and o.explanation
        assert all(k in INDICATORS for k in o.check + o.emergency_if_red)
        assert not o.hazard or o.hazard in HAZARDS
    for q in QUESTIONS.values():
        assert 2 <= len(q.options) <= 10


def test_red_flags_are_emergencies():
    for i in range(4):
        assert assess([i]).urgency == EMERGENCY


def _answers_to(outcome_id):
    return next(p for p, o in _paths() if o.id == outcome_id)


def test_walk_and_errors():
    steps, cur = walk([4])
    assert isinstance(cur, Question) and cur.id == "complaint" and steps[0][1].label == "None of these"
    with pytest.raises(ValueError):
        walk([99])
    with pytest.raises(ValueError):
        walk([0, 0])
    with pytest.raises(ValueError):
        assess([4])  # not finished


def test_motion_sickness_path_is_self_care_with_normal_vitals():
    a = assess(_answers_to("o_sms"), evaluate_snapshot({"heart_rate": 70}))
    assert a.outcome_id == "o_sms" and a.urgency == SELF
    assert a.answers[-1]["answer"] == "Yes" and a.evidence[0]["status"] == "green"


def test_vitals_raise_urgency_never_lower():
    path = _answers_to("o_uri")
    assert assess(path, evaluate_snapshot({"body_temp": 37.0, "spo2": 98})).urgency == SELF
    assert assess(path, evaluate_snapshot({"body_temp": 37.7, "spo2": 98})).urgency == CMO
    assert assess(path, evaluate_snapshot({"body_temp": 39.0, "spo2": 98})).urgency == SURGEON
    # breathing problem + red SpO2 -> emergency
    a = assess(_answers_to("o_dust"), evaluate_snapshot({"spo2": 88}))
    assert a.urgency == EMERGENCY and any("emergency" in n for n in a.notes)


def test_missing_measurements_are_flagged_and_comm_delay_note():
    a = assess(_answers_to("o_kidney_stone"), {}, environment="mars_base")
    assert a.urgency == SURGEON
    assert any("would make this assessment more reliable" in n for n in a.notes)
    assert any("Don't wait for an answer" in n for n in a.notes)
    assert not any("Don't wait" in n for n in assess(_answers_to("o_kidney_stone"), {}, "iss").notes)
