"""Generates recommendations for the astronaut from a HealthStatus."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.status import HealthStatus, Level, MetricStatus

DISCLAIMER = (
    "These recommendations are informational only; if in doubt, contact "
    "the flight surgeon at mission control."
)


@dataclass(frozen=True)
class Recommendation:
    level: Level
    category: str
    message: str
    escalate: bool = False  # If True, ground team / physician should be notified


# (metric, direction) -> advice text
ADVICE: dict[tuple[str, str], str] = {
    ("heart_rate", "high"): "Heart rate is high: rest, drink water, cut back on caffeine, and re-measure in 10 minutes.",
    ("heart_rate", "low"): "Heart rate is low: avoid sudden movements if you feel dizzy or weak, and re-measure.",
    ("systolic_bp", "high"): "Systolic blood pressure is high: reduce sodium intake, rest, and re-measure.",
    ("systolic_bp", "low"): "Systolic blood pressure is low: increase fluid intake and move slowly.",
    ("diastolic_bp", "high"): "Diastolic blood pressure is high: rest and re-measure in 15 minutes.",
    ("diastolic_bp", "low"): "Diastolic blood pressure is low: increase fluid intake and re-measure.",
    ("spo2", "low"): "Oxygen saturation is low: check cabin ventilation and CO2 levels, then re-measure.",
    ("body_temp", "high"): "You have a fever: watch for signs of infection, drink fluids, and re-measure periodically.",
    ("body_temp", "low"): "Body temperature is low: check cabin temperature and your clothing.",
    ("daily_exercise_min", "low"): "Exercise is insufficient: complete your daily resistance/cardio routine to prevent bone and muscle loss.",
    ("sleep_hours", "low"): "Sleep is insufficient: regularize your sleep schedule and reduce light and noise.",
    ("mood", "low"): "Mood is low: talk to a crewmate or the ground support team.",
    ("stress", "high"): "Stress is high: try a breathing exercise or a short break.",
    ("daily_radiation_msv", "high"): "Radiation dose is high: stay in a shielded module if possible and share the cumulative dose with the ground team.",
}

# From this level upward, the ground team is notified.
ESCALATION_LEVEL = Level.WARNING


def _single(m: MetricStatus) -> Recommendation:
    text = ADVICE.get(
        (m.name, m.direction or ""),
        f"{m.name} is outside the normal range ({m.value}); keep monitoring.",
    )
    return Recommendation(m.level, m.category, text, escalate=m.level >= ESCALATION_LEVEL)


def _combined(status: HealthStatus) -> list[Recommendation]:
    """Rules where several indicators together carry extra meaning."""
    m = status.metrics
    out: list[Recommendation] = []

    def abnormal(name: str, direction: str) -> bool:
        x = m.get(name)
        return x is not None and x.level > Level.NORMAL and x.direction == direction

    if abnormal("body_temp", "high") and abnormal("heart_rate", "high"):
        out.append(Recommendation(
            Level.WARNING, "immune",
            "Fever and elevated heart rate together: possible infection. Consult the medical team.",
            escalate=True,
        ))
    if abnormal("sleep_hours", "low") and abnormal("stress", "high"):
        out.append(Recommendation(
            Level.WARNING, "behavioral",
            "Insufficient sleep and high stress together: risk of burnout. Review your workload.",
            escalate=False,
        ))
    if abnormal("daily_exercise_min", "low") and abnormal("systolic_bp", "low"):
        out.append(Recommendation(
            Level.WATCH, "cardiovascular",
            "Low exercise and low blood pressure: possible cardiovascular deconditioning. Return to your exercise program.",
        ))
    return out


def recommend(status: HealthStatus) -> list[Recommendation]:
    """Return recommendations ordered from most to least severe.

    If nothing is wrong, a single NORMAL recommendation is returned.
    """
    recs = [_single(m) for m in status.abnormal()] + _combined(status)

    if not recs:
        return [Recommendation(Level.NORMAL, "general", "All indicators are normal. Continue your routine.")]

    if status.overall == Level.CRITICAL:
        recs.append(Recommendation(
            Level.CRITICAL, "general",
            "Critical value detected: contact the flight surgeon at mission control IMMEDIATELY.",
            escalate=True,
        ))

    return sorted(recs, key=lambda r: (-r.level, r.category, r.message))


def needs_escalation(recs: list[Recommendation]) -> bool:
    return any(r.escalate for r in recs)