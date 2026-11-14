"""Catalogue of health indicators, spaceflight hazards and body regions.

This is the "knowledge base" the UI uses to teach the astronaut *how* to
measure, *why* it matters and *which hazard* drives the risk. Nothing here
assumes the user is a medical expert.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# NASA Human Research Program: the five hazards of human spaceflight (RIDGE)
# --------------------------------------------------------------------------
HAZARDS: dict[str, dict[str, str]] = {
    "radiation": {
        "name": "Space radiation",
        "icon": "☢️",
        "summary": "Galactic cosmic rays and solar particle events raise cancer risk and can "
        "affect the central nervous system, heart and immune system.",
    },
    "isolation": {
        "name": "Isolation & confinement",
        "icon": "🧠",
        "summary": "Small crews in small volumes for months: sleep loss, circadian disruption, "
        "low mood, fatigue and team conflict.",
    },
    "distance": {
        "name": "Distance from Earth",
        "icon": "📡",
        "summary": "Communication delays and no quick return: the crew must detect and treat "
        "problems autonomously with limited supplies.",
    },
    "gravity": {
        "name": "Gravity fields",
        "icon": "🪐",
        "summary": "Microgravity and partial gravity shift body fluids, unload bones and muscles "
        "and decondition the heart; gravity transitions disturb balance.",
    },
    "environment": {
        "name": "Hostile & closed environment",
        "icon": "🛰️",
        "summary": "Recycled air (CO₂), noise, microbes, dust and food system limits affect "
        "immunity, nutrition and comfort.",
    },
}


@dataclass(frozen=True)
class Indicator:
    key: str
    name: str
    unit: str
    min_valid: float
    max_valid: float
    step: float
    default: float
    how_to_measure: str
    why_it_matters: str
    hazards: tuple[str, ...]
    region: str
    decimals: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)

    def format(self, value: float | None) -> str:
        if value is None or value != value:
            return "—"
        return f"{value:.{self.decimals}f} {self.unit}".strip()


INDICATORS: dict[str, Indicator] = {
    i.key: i
    for i in [
        Indicator(
            key="heart_rate",
            name="Resting heart rate",
            unit="bpm",
            min_valid=20,
            max_valid=250,
            step=1,
            default=65,
            how_to_measure="Right after waking, before coffee or exercise. Sit still for 5 minutes, "
            "then read the wrist monitor or count the radial pulse for 30 s and multiply by 2.",
            why_it_matters="Fluid shifts and heart deconditioning in microgravity change resting heart "
            "rate. A rising trend can signal fever, dehydration, stress or overtraining.",
            hazards=("gravity", "isolation", "radiation"),
            region="heart",
            tags=("morning", "core"),
        ),
        Indicator(
            key="systolic_bp",
            name="Blood pressure — systolic",
            unit="mmHg",
            min_valid=50,
            max_valid=260,
            step=1,
            default=118,
            how_to_measure="Seated with the back supported (use foot loops), cuff on the bare upper arm "
            "at heart level. Rest 5 min, do not talk. Take two readings 1 min apart and log the average.",
            why_it_matters="Head-ward fluid shift and cardiovascular deconditioning change blood "
            "pressure; high values plus headache can also point to CO₂ build-up.",
            hazards=("gravity", "environment"),
            region="heart",
            tags=("morning", "core"),
        ),
        Indicator(
            key="diastolic_bp",
            name="Blood pressure — diastolic",
            unit="mmHg",
            min_valid=30,
            max_valid=160,
            step=1,
            default=76,
            how_to_measure="Recorded together with systolic pressure — the lower of the two numbers "
            "shown by the cuff.",
            why_it_matters="Together with systolic pressure it describes the load on the heart and "
            "vessels.",
            hazards=("gravity",),
            region="heart",
            tags=("morning", "core"),
        ),
        Indicator(
            key="spo2",
            name="Oxygen saturation (SpO₂)",
            unit="%",
            min_valid=50,
            max_valid=100,
            step=1,
            default=98,
            how_to_measure="Clip the pulse oximeter on a warm finger (no nail polish), keep the hand "
            "still for 30 s and log the stable value.",
            why_it_matters="Detects problems with cabin atmosphere, lungs or circulation early — "
            "critical in a closed life-support system.",
            hazards=("environment",),
            region="lungs",
            tags=("morning", "core"),
        ),
        Indicator(
            key="body_temp",
            name="Body temperature",
            unit="°C",
            min_valid=30,
            max_valid=44,
            step=0.1,
            default=36.7,
            how_to_measure="Oral or ear thermometer before eating or drinking. Note it if you just "
            "exercised — wait 30 min in that case.",
            why_it_matters="The immune system is altered in spaceflight and latent viruses can "
            "reactivate; fever is often the first sign of infection.",
            hazards=("environment", "radiation"),
            region="immune",
            decimals=1,
            tags=("morning", "core"),
        ),
        Indicator(
            key="blood_glucose",
            name="Fasting blood glucose",
            unit="mg/dL",
            min_valid=20,
            max_valid=600,
            step=1,
            default=90,
            how_to_measure="Fasting (no food for 8 h). Wash and dry the finger, use a lancet on the "
            "side of the fingertip, touch the strip to the drop. Capture the drop quickly — liquids "
            "do not fall in microgravity.",
            why_it_matters="Inactivity and altered diet reduce insulin sensitivity in flight; low "
            "glucose impairs judgement during critical tasks.",
            hazards=("gravity", "environment"),
            region="metabolism",
            tags=("morning", "core"),
        ),
        Indicator(
            key="sleep_hours",
            name="Sleep",
            unit="h",
            min_valid=0,
            max_valid=24,
            step=0.25,
            default=7.5,
            how_to_measure="Hours actually asleep in the last 24 h (actigraphy watch or your best "
            "estimate). Include naps.",
            why_it_matters="Light/dark cycles every 90 min in orbit, noise and workload cause chronic "
            "sleep loss, which drives errors, low mood and weaker immunity.",
            hazards=("isolation", "environment"),
            region="brain",
            decimals=1,
            tags=("morning", "core"),
        ),
        Indicator(
            key="mood",
            name="Mood",
            unit="/5",
            min_valid=1,
            max_valid=5,
            step=1,
            default=4,
            how_to_measure="How do you feel right now? 1 = very low, 2 = low, 3 = neutral, "
            "4 = good, 5 = very good. Be honest — this is for you.",
            why_it_matters="Isolation, confinement and distance from family can lead to depression, "
            "anxiety and crew conflict. Early self-awareness is the best countermeasure.",
            hazards=("isolation", "distance"),
            region="brain",
            tags=("evening", "core"),
        ),
        Indicator(
            key="exercise_minutes",
            name="Countermeasure exercise",
            unit="min",
            min_valid=0,
            max_valid=480,
            step=5,
            default=90,
            how_to_measure="Total minutes of resistive (ARED-type) plus aerobic (treadmill/cycle) "
            "exercise completed today.",
            why_it_matters="Without loading, weight-bearing bones lose ~1–1.5 % mineral density per "
            "month and muscles atrophy. Exercise is the main countermeasure.",
            hazards=("gravity",),
            region="musculoskeletal",
            tags=("evening", "core"),
        ),
        Indicator(
            key="radiation_dose",
            name="Radiation dose (24 h)",
            unit="mSv",
            min_valid=0,
            max_valid=1000,
            step=0.05,
            default=0.5,
            how_to_measure="Read your personal active dosimeter and log the dose accumulated over the "
            "last 24 h.",
            why_it_matters="Radiation exposure adds up over the career. Sudden spikes mean a solar "
            "particle event — move to the shielded shelter.",
            hazards=("radiation",),
            region="whole_body",
            decimals=2,
            tags=("evening",),
        ),
    ]
}

CORE_INDICATORS = [k for k, i in INDICATORS.items() if "core" in i.tags]

# --------------------------------------------------------------------------
# Body regions shown on the interactive body map
# --------------------------------------------------------------------------
REGIONS: dict[str, dict] = {
    "brain": {
        "name": "Brain & behaviour",
        "function": "Controls thinking, sleep–wake cycles, mood and coordination.",
        "space_effects": "Disrupted circadian rhythm, sleep loss, stress, isolation-related mood "
        "changes, vestibular (balance) adaptation after gravity transitions.",
        "indicators": ["sleep_hours", "mood"],
    },
    "heart": {
        "name": "Heart & blood vessels",
        "function": "Pumps blood to deliver oxygen and nutrients to every organ.",
        "space_effects": "Fluids move toward the head, total blood volume drops and the heart "
        "deconditions; risk of dizziness on return to gravity.",
        "indicators": ["heart_rate", "systolic_bp", "diastolic_bp"],
    },
    "lungs": {
        "name": "Lungs & breathing",
        "function": "Exchange oxygen and carbon dioxide with the cabin air.",
        "space_effects": "Depend entirely on the life-support system; dust (lunar/Martian) and "
        "CO₂ build-up are the main threats.",
        "indicators": ["spo2"],
    },
    "metabolism": {
        "name": "Metabolism & nutrition",
        "function": "Turns food into energy and keeps blood sugar stable.",
        "space_effects": "Reduced appetite, limited menu, inactivity and stress hormones reduce "
        "insulin sensitivity.",
        "indicators": ["blood_glucose"],
    },
    "immune": {
        "name": "Immune system",
        "function": "Defends against infections and repairs tissue.",
        "space_effects": "Stress, radiation and microgravity dysregulate immunity; latent viruses "
        "(e.g. herpes viruses) can reactivate.",
        "indicators": ["body_temp"],
    },
    "musculoskeletal": {
        "name": "Bones & muscles",
        "function": "Support the body, enable movement and store calcium.",
        "space_effects": "Weight-bearing bones lose 1–1.5 % mineral density per month; leg and "
        "back muscles atrophy without daily exercise. Kidney-stone risk rises.",
        "indicators": ["exercise_minutes"],
    },
    "whole_body": {
        "name": "Whole-body radiation",
        "function": "Every cell is exposed to radiation passing through the spacecraft.",
        "space_effects": "Cumulative dose increases long-term cancer and cardiovascular risk; "
        "solar particle events can cause acute effects without shelter.",
        "indicators": ["radiation_dose"],
    },
}


def indicators_for_region(region: str) -> list[Indicator]:
    return [INDICATORS[k] for k in REGIONS[region]["indicators"]]


def validate_value(indicator: str, value: float) -> None:
    """Raise ``ValueError`` for unknown indicators or physically implausible values."""
    if indicator not in INDICATORS:
        raise ValueError(f"Unknown indicator: {indicator!r}")
    ind = INDICATORS[indicator]
    if not (ind.min_valid <= value <= ind.max_valid):
        raise ValueError(
            f"{ind.name} value {value} outside plausible range "
            f"[{ind.min_valid}, {ind.max_valid}] {ind.unit}"
        )
