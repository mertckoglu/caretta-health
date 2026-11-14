"""Traffic-light thresholds for every health indicator.

Every indicator has a list of *green* bands and *yellow* bands. A band is a
half-open interval ``[low, high)``. Any valid value outside green and yellow is
*red*. Bands are deliberately conservative screening limits for a healthy,
medically-selected adult crew member; they are NOT diagnostic criteria.
Sources are listed in ``data/thresholds_sources.md``.

Some limits depend on where the crew is (a radiation dose that is routine
in deep-space transit would be unusual in low Earth orbit), so each
environment can override the base table.
"""
from __future__ import annotations

from copy import deepcopy
from math import inf

GREEN = "green"
YELLOW = "yellow"
RED = "red"
UNKNOWN = "unknown"

#: Ordering used to pick the "worst" status. Unknown never outranks a real result.
SEVERITY = {UNKNOWN: 0, GREEN: 1, YELLOW: 2, RED: 3}

STATUS_LABELS = {
    GREEN: "Nominal",
    YELLOW: "Watch",
    RED: "Act now",
    UNKNOWN: "No data",
}

Band = tuple[float, float]

BASE_THRESHOLDS: dict[str, dict[str, list[Band]]] = {
    # Resting heart rate, beats per minute
    "heart_rate": {"green": [(50, 100)], "yellow": [(40, 50), (100, 120)]},
    # Blood pressure, mmHg (seated, rested 5 min)
    "systolic_bp": {"green": [(90, 130)], "yellow": [(85, 90), (130, 160)]},
    "diastolic_bp": {"green": [(60, 80)], "yellow": [(55, 60), (80, 100)]},
    # Peripheral oxygen saturation, %
    "spo2": {"green": [(95, inf)], "yellow": [(92, 95)]},
    # Core / oral body temperature, °C
    "body_temp": {"green": [(36.1, 37.5)], "yellow": [(35.5, 36.1), (37.5, 38.0)]},
    # Fasting capillary blood glucose, mg/dL
    "blood_glucose": {"green": [(70, 100)], "yellow": [(54, 70), (100, 180)]},
    # Sleep in the last 24 h, hours
    "sleep_hours": {"green": [(7, 9.5)], "yellow": [(5.5, 7), (9.5, 11)]},
    # Self-rated mood, 1 (very low) .. 5 (very good)
    "mood": {"green": [(4, inf)], "yellow": [(2, 4)]},
    # Countermeasure exercise completed today, minutes
    "exercise_minutes": {"green": [(90, inf)], "yellow": [(30, 90)]},
    # Personal dosimeter, dose in the last 24 h, mSv
    "radiation_dose": {"green": [(0, 1.0)], "yellow": [(1.0, 5.0)]},
}

ENVIRONMENTS: dict[str, dict] = {
    "iss": {
        "label": "Space station (LEO)",
        "gravity_g": 0.0,
        "typical_dose_msv_day": 0.5,
        "one_way_delay_min": (0, 0),
        "typical_exercise_min": 120,
        "notes": "Microgravity, partial magnetospheric shielding, ~2 h/day exercise schedule.",
    },
    "transit": {
        "label": "Spacecraft — deep-space transit",
        "gravity_g": 0.0,
        "typical_dose_msv_day": 1.8,
        "one_way_delay_min": (1, 22),
        "typical_exercise_min": 75,
        "notes": "No magnetospheric shielding; solar particle events require storm shelter.",
    },
    "lunar_base": {
        "label": "Lunar surface base",
        "gravity_g": 0.17,
        "typical_dose_msv_day": 1.3,
        "one_way_delay_min": (0.02, 0.03),
        "typical_exercise_min": 75,
        "notes": "1/6 g, regolith dust, long lunar night affects circadian rhythm.",
    },
    "mars_base": {
        "label": "Mars surface base",
        "gravity_g": 0.38,
        "typical_dose_msv_day": 0.7,
        "one_way_delay_min": (4, 24),
        "typical_exercise_min": 75,
        "notes": "3/8 g, 4–24 min one-way comms delay: the crew must act autonomously.",
    },
    "rover": {
        "label": "Pressurised rover / EVA sortie",
        "gravity_g": 0.17,
        "typical_dose_msv_day": 1.3,
        "one_way_delay_min": (0.02, 0.03),
        "typical_exercise_min": 40,
        "notes": "Small cabin, limited exercise equipment, high workload days.",
    },
}

DEFAULT_ENVIRONMENT = "iss"

ENV_OVERRIDES: dict[str, dict[str, dict[str, list[Band]]]] = {
    "transit": {
        "radiation_dose": {"green": [(0, 2.5)], "yellow": [(2.5, 10.0)]},
        "exercise_minutes": {"green": [(60, inf)], "yellow": [(30, 60)]},
    },
    "lunar_base": {
        "radiation_dose": {"green": [(0, 2.0)], "yellow": [(2.0, 10.0)]},
        "exercise_minutes": {"green": [(60, inf)], "yellow": [(30, 60)]},
    },
    "mars_base": {
        "exercise_minutes": {"green": [(60, inf)], "yellow": [(30, 60)]},
    },
    "rover": {
        "radiation_dose": {"green": [(0, 2.0)], "yellow": [(2.0, 10.0)]},
        "exercise_minutes": {"green": [(30, inf)], "yellow": [(15, 30)]},
    },
}

#: NASA-STD-3001 career effective dose limit (all ages and sexes), mSv.
CAREER_DOSE_LIMIT_MSV = 600.0


def get_thresholds(indicator: str, environment: str = DEFAULT_ENVIRONMENT) -> dict[str, list[Band]]:
    """Return the green/yellow bands for ``indicator`` in ``environment``."""
    if indicator not in BASE_THRESHOLDS:
        raise KeyError(f"Unknown indicator: {indicator!r}")
    bands = deepcopy(BASE_THRESHOLDS[indicator])
    bands.update(deepcopy(ENV_OVERRIDES.get(environment, {}).get(indicator, {})))
    return bands


def _in_any(value: float, bands: list[Band]) -> bool:
    return any(low <= value < high for low, high in bands)


def classify(indicator: str, value: float | None, environment: str = DEFAULT_ENVIRONMENT) -> str:
    """Classify a single value as green / yellow / red (or unknown if missing)."""
    if value is None or value != value:  # None or NaN
        return UNKNOWN
    bands = get_thresholds(indicator, environment)
    if _in_any(value, bands["green"]):
        return GREEN
    if _in_any(value, bands["yellow"]):
        return YELLOW
    return RED


def direction(indicator: str, value: float, environment: str = DEFAULT_ENVIRONMENT) -> str:
    """'low', 'high' or 'ok' relative to the green range."""
    green = get_thresholds(indicator, environment)["green"]
    low = min(b[0] for b in green)
    high = max(b[1] for b in green)
    if value < low:
        return "low"
    if value >= high:
        return "high"
    return "ok"


def green_range(indicator: str, environment: str = DEFAULT_ENVIRONMENT) -> Band:
    green = get_thresholds(indicator, environment)["green"]
    return min(b[0] for b in green), max(b[1] for b in green)


def worst(statuses) -> str:
    """Worst status in an iterable; ``unknown`` if empty or all unknown."""
    result = UNKNOWN
    for s in statuses:
        if SEVERITY[s] > SEVERITY[result]:
            result = s
    return result
