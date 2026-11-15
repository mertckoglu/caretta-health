"""Synthetic but physiologically plausible mission data for demos and tests.

The generator layers known spaceflight effects on top of a healthy baseline:

* early-mission fluid shift: slightly lower heart rate & diastolic pressure,
* gradual sleep erosion over the mission (workload, light cycles),
* the "third-quarter phenomenon" — a mood dip after the mission mid-point,
* scripted events: a solar particle event (radiation spike), a febrile
  infection, a missed-exercise period (equipment failure).

Every mission environment has its own :data:`ENV_PROFILES` entry, so the same
crew produces different data on the ISS, in deep space, on the Moon, on Mars
or in a rover (radiation, gravity loading, isolation, dust, workload…).

Output is a *long* DataFrame: ``ts, astronaut_id, environment, indicator, value``.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from app.core.indicators import INDICATORS
from app.core.thresholds import DEFAULT_ENVIRONMENT, ENVIRONMENTS

MORNING = {"heart_rate", "systolic_bp", "diastolic_bp", "spo2", "body_temp", "blood_glucose", "sleep_hours"}

DEFAULT_EVENTS = {
    "spe_day": 12,  # solar particle event
    "fever_days": (22, 23),  # infection
    "missed_exercise_days": (16, 17, 18),  # treadmill out of service
}

#: How each environment modifies the healthy baseline. Keys not given default to 0 / 1.
ENV_PROFILES: dict[str, dict] = {
    "iss": {
        "story": "ISS increment: treadmill failure (days 16–18), solar particle event (day 12), "
                 "fever (days 22–23), mid-mission mood dip.",
        "events": DEFAULT_EVENTS,
        "spe_msv": 6.5,
    },
    "transit": {
        "story": "Deep-space transit: no magnetosphere — strong solar particle event (day 12–13) "
                 "and storm-shelter nights, stronger isolation mood dip, compact exercise device.",
        "events": {"spe_day": 12, "fever_days": (22, 23)},
        "spe_msv": 14.0, "spe_after_msv": 3.0, "spe_sleep_loss": 2.0,
        "mood_dip": 1.8, "sleep": -0.1, "hr": -2,
    },
    "lunar_base": {
        "story": "Lunar base: regolith dust exposure after EVAs (days 8–9, SpO₂ dip), long lunar "
                 "night from day 15 (sleep erosion), solar particle event (day 12).",
        "events": {"spe_day": 12, "fever_days": (22, 23), "dust_days": (8, 9), "night_from": 15},
        "spe_msv": 9.0, "hr": 2, "spo2": -0.4,
    },
    "mars_base": {
        "story": "Mars base: 4–24 min comm delay — strongest isolation mood dip, dust storm "
                 "(days 10–14) limiting exercise, irregular 24 h 39 min sol sleep, mild SPE (day 12).",
        "events": {"spe_day": 12, "fever_days": (22, 23), "storm_days": (10, 11, 12, 13, 14)},
        "spe_msv": 3.0, "mood_dip": 2.2, "sleep_sd": 0.8, "hr": 1,
    },
    "rover": {
        "story": "Pressurised rover traverse: EVA every third day (heart rate, glucose up), short "
                 "sleep in a cramped cabin, cabin CO₂ build-up (day 18–19), limited exercise.",
        "events": {"spe_day": 12, "fever_days": (22, 23), "co2_days": (18, 19), "eva_every": 3},
        "spe_msv": 9.0, "sleep": -0.15, "sbp": 6, "glucose": 3, "spo2": -0.3,
    },
}


def _clip(indicator: str, value: float) -> float:
    ind = INDICATORS[indicator]
    v = float(np.clip(value, ind.min_valid, ind.max_valid))
    return round(v, ind.decimals)


def simulate_day(
    day_index: int,
    days: int,
    rng: np.random.Generator,
    environment: str = DEFAULT_ENVIRONMENT,
    events: dict | None = None,
) -> dict[str, float]:
    """Values for one mission day (0-based ``day_index``)."""
    prof = ENV_PROFILES.get(environment, ENV_PROFILES[DEFAULT_ENVIRONMENT])
    ev = prof["events"] if events is None else events
    frac = day_index / max(days - 1, 1)
    env = ENVIRONMENTS.get(environment, ENVIRONMENTS[DEFAULT_ENVIRONMENT])
    adapt = np.exp(-day_index / 4)  # first days of adaptation

    fever = day_index in ev.get("fever_days", ())
    spe = day_index == ev.get("spe_day")
    spe_after = ev.get("spe_day") is not None and day_index == ev["spe_day"] + 1
    no_ex = day_index in ev.get("missed_exercise_days", ())
    dust = day_index in ev.get("dust_days", ())
    storm = day_index in ev.get("storm_days", ())
    co2 = day_index in ev.get("co2_days", ())
    night = ev.get("night_from") is not None and day_index >= ev["night_from"]
    eva = bool(ev.get("eva_every")) and day_index % ev["eva_every"] == 1

    # third-quarter phenomenon: mood dip centred at 65 % of the mission (stronger when isolated)
    mood_dip = 1.4 * prof.get("mood_dip", 1.0) * np.exp(-((frac - 0.65) ** 2) / 0.006)
    sleep = (7.4 + prof.get("sleep", 0) - 0.9 * frac - 0.6 * adapt + rng.normal(0, prof.get("sleep_sd", 0.5))
             - (0.8 if fever else 0) - (prof.get("spe_sleep_loss", 0) if spe else 0)
             - (0.45 if night else 0) - (0.6 if co2 else 0))
    hr = (62 + prof.get("hr", 0) - 3 * adapt + rng.normal(0, 3) + (16 if fever else 0)
          + 4 * min(mood_dip, 1.4) / 1.4 + (9 if eva else 0) + (5 if co2 else 0))
    temp = 36.7 + rng.normal(0, 0.15) + (1.5 if fever else 0)
    exercise = env.get("typical_exercise_min", 120) + rng.normal(0, 15)
    if no_ex:
        exercise = rng.choice([0, 15, 20])
    elif storm:
        exercise = rng.choice([20, 25, 30, 35])
    elif eva:
        exercise = max(exercise, 60 + rng.normal(0, 10))  # EVA work counts as exercise
    radiation = env["typical_dose_msv_day"] * (1 + rng.normal(0, 0.08))
    radiation += prof.get("spe_msv", 6.5) if spe else 0
    radiation += prof.get("spe_after_msv", 0) if spe_after else 0
    values = {
        "heart_rate": hr,
        "systolic_bp": 116 + prof.get("sbp", 0) + rng.normal(0, 5) + 3 * frac + (8 if co2 else 0),
        "diastolic_bp": 74 - 3 * adapt + rng.normal(0, 4) + (4 if co2 else 0),
        "spo2": 98 + prof.get("spo2", 0) + rng.normal(0, 0.7) - (4.0 if dust else 0) - (3.6 if co2 else 0),
        "body_temp": temp,
        "blood_glucose": 88 + prof.get("glucose", 0) + 6 * frac + rng.normal(0, 6) + (14 if eva else 0),
        "sleep_hours": sleep,
        "mood": 4.4 - mood_dip + rng.normal(0, 0.45) - (1 if fever else 0) - (0.6 if storm else 0),
        "exercise_minutes": exercise - (60 if fever else 0),
        "radiation_dose": radiation,
    }
    values["mood"] = round(float(np.clip(values["mood"], 1, 5)))
    values["spo2"] = min(values["spo2"], 100)
    values["exercise_minutes"] = 5 * round(max(values["exercise_minutes"], 0) / 5)
    return {k: _clip(k, v) for k, v in values.items()}


def simulate_mission(
    days: int = 30,
    astronaut_id: str = "CDR",
    environment: str = DEFAULT_ENVIRONMENT,
    seed: int = 42,
    start: date | None = None,
    events: dict | None = None,
) -> pd.DataFrame:
    """Generate ``days`` daily reports ending yesterday (or starting at ``start``).

    One value per indicator per day, stamped at midnight — the same shape as a real check-in.
    Today is left empty on purpose: it belongs to the astronaut's own check-in.
    """
    rng = np.random.default_rng(seed)
    start = start or (date.today() - timedelta(days=days))
    rows = []
    for d in range(days):
        day = start + timedelta(days=d)
        values = simulate_day(d, days, rng, environment, events)
        for ind, v in values.items():
            rows.append(
                {
                    "ts": datetime.combine(day, time()),
                    "astronaut_id": astronaut_id,
                    "environment": environment,
                    "indicator": ind,
                    "value": v,
                }
            )
    return pd.DataFrame(rows)


def simulate_crew(
    crew: tuple[str, ...] = ("CDR", "PLT", "MS1", "MS2"),
    days: int = 30,
    environment: str = DEFAULT_ENVIRONMENT,
    seed: int = 42,
    start: date | None = None,
) -> pd.DataFrame:
    """One dataset per crew member for ``environment`` (different seed per environment)."""
    frames = []
    for i, member in enumerate(crew):
        prof_events = ENV_PROFILES.get(environment, ENV_PROFILES[DEFAULT_ENVIRONMENT])["events"]
        # commander: every scripted event; others share the environment-wide ones (SPE, dust, storm, CO₂, EVA)
        events = prof_events if i == 0 else {k: v for k, v in prof_events.items()
                                             if k not in ("fever_days", "missed_exercise_days")}
        env_seed = seed + 100 * list(ENVIRONMENTS).index(environment) if environment in ENVIRONMENTS else seed
        frames.append(simulate_mission(days, member, environment, env_seed + i, start, events))
    return pd.concat(frames, ignore_index=True)
