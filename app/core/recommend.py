"""Actionable guidance, daily routine prompts, gamification and downlink report.

The guidance is written for a non-specialist and always says *who* should act:
the astronaut, the crew medical officer (CMO), or the flight surgeon on Earth.
It supports — never replaces — the mission's medical checklists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from app.core.companion import alert_text, lc
from app.core.companion import overall as companion_overall
from app.core.indicators import CORE_INDICATORS, INDICATORS
from app.core.status import IndicatorStatus, TrendAlert, normalize
from app.core.thresholds import (
    DEFAULT_ENVIRONMENT,
    GREEN,
    RED,
    SEVERITY,
    UNKNOWN,
    YELLOW,
    direction,
    green_range,
    status_label,
)

SELF = "self"
CMO = "crew medical officer"
SURGEON = "flight surgeon"

# indicator -> direction -> status -> list of actions
GUIDANCE: dict[str, dict[str, dict[str, list[str]]]] = {
    "heart_rate": {
        "low": {
            YELLOW: [
                "Re-measure after sitting up for 5 minutes.",
                "A low resting rate is often normal for very fit crew — note any dizziness or fatigue.",
            ],
            RED: [
                "Stop strenuous activity and re-measure now.",
                "If dizzy, faint or short of breath: tell the CMO immediately and record an ECG.",
            ],
        },
        "high": {
            YELLOW: [
                "Re-measure after 10 minutes of quiet rest.",
                "Drink 500 mL of water; check temperature and recent sleep.",
                "Avoid caffeine for the rest of the day.",
            ],
            RED: [
                "Rest and re-measure in 5 minutes.",
                "If still high or with chest pain/palpitations: inform the CMO and record an ECG.",
                "Flight surgeon consultation at the next comm pass.",
            ],
        },
    },
    "systolic_bp": {
        "low": {
            YELLOW: [
                "Increase fluid and salt intake per mission diet plan.",
                "Move slowly when changing posture (especially in partial gravity).",
            ],
            RED: [
                "Lie down / restrain in a reclined position and raise the legs.",
                "Drink 1 L of fluid with electrolytes; inform the CMO.",
            ],
        },
        "high": {
            YELLOW: [
                "Repeat measurement after 5 min of rest.",
                "Check cabin CO₂ level — headaches plus high pressure can be CO₂-related.",
                "Reduce sodium in today's menu and practise slow breathing.",
            ],
            RED: [
                "Repeat measurement on the other arm.",
                "If headache, vision change or chest pain: inform the CMO now.",
                "Flight surgeon consultation required.",
            ],
        },
    },
    "diastolic_bp": {
        "low": {
            YELLOW: ["Hydrate and re-measure later today."],
            RED: ["Rest in a reclined position, hydrate and inform the CMO."],
        },
        "high": {
            YELLOW: ["Re-measure after rest; reduce sodium and caffeine."],
            RED: ["Re-measure; if confirmed, inform the CMO and flight surgeon."],
        },
    },
    "spo2": {
        "low": {
            YELLOW: [
                "Warm your hands and re-measure on another finger.",
                "Check cabin O₂/CO₂ readings on the ECLSS display.",
                "Ask a crewmate to measure too: if theirs is low as well, suspect the atmosphere.",
            ],
            RED: [
                "Go to fresh air flow / apply supplemental oxygen per emergency procedure.",
                "Alert the crew and the CMO immediately — check life support.",
            ],
        },
    },
    "body_temp": {
        "low": {
            YELLOW: ["Add a layer of clothing, drink something warm and re-measure in 30 min."],
            RED: ["Warm up actively, inform the CMO and re-measure every 15 min."],
        },
        "high": {
            YELLOW: [
                "Rest, hydrate and re-measure in 2 hours.",
                "Wash hands often and wipe shared surfaces to protect crewmates.",
            ],
            RED: [
                "Fever: inform the CMO, consider antipyretic from the medical kit per checklist.",
                "Limit close contact with the crew and wear a mask in shared modules.",
                "Flight surgeon consultation — may require a sample for the infection kit.",
            ],
        },
    },
    "blood_glucose": {
        "low": {
            YELLOW: [
                "Eat 15 g of fast carbohydrate (e.g. juice pouch) and re-test in 15 min.",
                "Don't start EVA or robotics tasks until back in range.",
            ],
            RED: [
                "Take 15–20 g of fast carbohydrate NOW and re-test in 15 min.",
                "Tell a crewmate; inform the CMO if not back above 70 mg/dL.",
            ],
        },
        "high": {
            YELLOW: [
                "Confirm you were fasting; re-test tomorrow morning.",
                "Keep up countermeasure exercise — it improves insulin sensitivity.",
            ],
            RED: [
                "Re-test with a new strip after washing hands.",
                "If confirmed, inform the CMO; flight surgeon review of diet and medication.",
            ],
        },
    },
    "sleep_hours": {
        "low": {
            YELLOW: [
                "Protect the next sleep period: eye mask, earplugs, sleep station door closed.",
                "Avoid screens 1 h before sleep; use the circadian lighting schedule.",
                "A 20-minute nap before a demanding task is OK.",
            ],
            RED: [
                "Inform the crew: avoid safety-critical tasks (EVA, docking, robotics) if possible.",
                "Ask the CMO/ground about schedule adjustment; sleep medication only per protocol.",
            ],
        },
        "high": {
            YELLOW: ["Unusually long sleep can signal illness or low mood — check temperature and mood."],
            RED: ["Very long sleep: check for illness and inform the CMO."],
        },
    },
    "mood": {
        "low": {
            YELLOW: [
                "Schedule some personal time: music, a call with family, a look out the window.",
                "Share a meal with the crew; physical exercise also improves mood.",
            ],
            RED: [
                "Talk to someone today — a crewmate, the CMO or the behavioural health team.",
                "Request a private psychological conference at the next comm pass.",
            ],
        },
    },
    "exercise_minutes": {
        "low": {
            YELLOW: [
                "Add a short session today: 30 min resistive exercise protects bones and muscle.",
                "Plan tomorrow's session at a fixed time.",
            ],
            RED: [
                "Missed countermeasure: make it up today if workload allows.",
                "If equipment is down, report it — ground will provide an alternative protocol.",
            ],
        },
    },
    "radiation_dose": {
        "high": {
            YELLOW: [
                "Check the space-weather alert; spend sleep periods in the best-shielded area.",
                "Log your location for the day so dose can be reconstructed.",
            ],
            RED: [
                "Possible solar particle event: go to the storm shelter NOW.",
                "Inform the crew and ground; postpone EVA.",
            ],
        },
    },
}

GREEN_TIPS = {
    "heart_rate": "Nice — keep the same measurement routine so trends stay comparable.",
    "systolic_bp": "In range. Keep hydration and exercise steady.",
    "diastolic_bp": "In range.",
    "spo2": "Good oxygenation.",
    "body_temp": "No sign of fever.",
    "blood_glucose": "Stable blood sugar — keep eating the full menu.",
    "sleep_hours": "Well rested. Protect this routine.",
    "mood": "Good to hear! Share it with the crew.",
    "exercise_minutes": "Countermeasure goal met — your bones thank you.",
    "radiation_dose": "Dose within the expected range for this environment.",
}


@dataclass
class Recommendation:
    indicator: str
    status: str
    title: str
    actions: list[str] = field(default_factory=list)
    contact: str = SELF
    escalate: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def recommend(
    indicator: str, value: float | None, status: str, environment: str = DEFAULT_ENVIRONMENT
) -> Recommendation:
    ind = INDICATORS[indicator]
    if status == UNKNOWN or value is None:
        return Recommendation(
            indicator,
            UNKNOWN,
            f"We don't have a recent {lc(ind.name)} reading yet",
            [f"How to measure: {ind.how_to_measure}"],
        )
    if status == GREEN:
        return Recommendation(indicator, GREEN, f"Your {lc(ind.name)} looks steady", [GREEN_TIPS[indicator]])

    d = direction(indicator, value, environment)
    lo, hi = green_range(indicator, environment)
    target = f"usually {lo:g}–{hi:g} {ind.unit}" if hi != float("inf") else f"usually {lo:g} {ind.unit} or more"
    actions = GUIDANCE.get(indicator, {}).get(d, {}).get(status) or [
        "Re-measure and inform the crew medical officer if it persists."
    ]
    contact = SURGEON if status == RED else (CMO if indicator in ("spo2", "body_temp") else SELF)
    word = "low" if d == "low" else "high"
    return Recommendation(
        indicator,
        status,
        f"Your {lc(ind.name)} is {word} at {ind.format(value)} ({target})",
        list(actions),
        contact,
        escalate=status == RED,
    )


def recommendations_for(
    statuses: dict[str, IndicatorStatus],
    alerts: list[TrendAlert] | None = None,
    environment: str = DEFAULT_ENVIRONMENT,
    include_green: bool = False,
) -> list[Recommendation]:
    recs = []
    for s in statuses.values():
        if s.status == GREEN and not include_green:
            continue
        if s.status == UNKNOWN:
            continue
        recs.append(recommend(s.indicator, s.value, s.status, environment))
    for a in alerts or []:
        headline, message = alert_text(a)
        recs.append(
            Recommendation(
                a.indicator,
                a.status,
                headline,
                [message],
                SURGEON if a.status == RED else CMO,
                escalate=a.status == RED,
            )
        )
    note = autonomy_note(environment)
    if note:
        for r in recs:
            if r.escalate:
                r.actions.append(note)
    recs.sort(key=lambda r: -SEVERITY[r.status])
    return recs


def autonomy_note(environment: str) -> str | None:
    """Extra instruction when the flight surgeon cannot answer quickly (communication delay)."""
    from app.core.thresholds import ENVIRONMENTS

    lo, hi = ENVIRONMENTS.get(environment, {}).get("one_way_delay_min", (0, 0))
    if hi < 1:
        return None
    return (f"Communication delay {lo:g}–{hi:g} min one way (round trip up to {2 * hi:g} min): "
            "do not wait for ground — start the on-board medical checklist with the CMO now.")


# ------------------------------------------------------- daily routine --
DAILY_TASKS = [
    {"id": "morning_vitals", "label": "Morning vitals (HR, BP, SpO₂, temperature)", "hour": 7,
     "indicators": ["heart_rate", "systolic_bp", "diastolic_bp", "spo2", "body_temp"]},
    {"id": "fasting_glucose", "label": "Fasting blood glucose", "hour": 7,
     "indicators": ["blood_glucose"]},
    {"id": "sleep_log", "label": "Log last night's sleep", "hour": 8,
     "indicators": ["sleep_hours"]},
    {"id": "exercise", "label": "Countermeasure exercise", "hour": 17,
     "indicators": ["exercise_minutes"]},
    {"id": "evening_checkin", "label": "Evening mood check-in", "hour": 20,
     "indicators": ["mood"]},
    {"id": "dosimeter", "label": "Dosimeter read-out", "hour": 21,
     "indicators": ["radiation_dose"]},
]


def task_progress(df: pd.DataFrame, day: date | None = None, now: datetime | None = None) -> list[dict]:
    """Which routine tasks are done / due / upcoming for ``day``."""
    now = now or datetime.now()
    day = day or now.date()
    df = normalize(df)
    logged = set(df[df["ts"].dt.date == day]["indicator"]) if not df.empty else set()
    out = []
    for t in DAILY_TASKS:
        done = all(i in logged for i in t["indicators"])
        if done:
            state = "done"
        elif day < now.date() or now.hour >= t["hour"]:
            state = "due"
        else:
            state = "upcoming"
        out.append({**t, "state": state})
    return out


# ------------------------------------------------------- weekly review --
# A plain, everyday routine tracker instead of points and badges. Each habit has a
# target taken from an established recommendation, and the review simply reports how
# many days of the week the target was met — like a health app or a training log.
#
#   Measurements  ≥ 80 % of the planned routine done   (80 % is the usual adherence cut-off in
#                                                       clinical self-monitoring studies)
#   Sleep         ≥ 7 h, on at least 5 of 7 nights     (AASM/SRS adult recommendation)
#   Exercise      environment's daily target, ≥ 5/7    (ISS crews train ~6 days a week)
#   Full check-in all core measurements on ≥ 5/7 days
REVIEW_DAYS = 7
ADHERENCE_GOOD, ADHERENCE_FAIR = 0.8, 0.5
SLEEP_TARGET_H = 7.0
DAYS_GOAL = 5          # out of 7


def streak_days(df: pd.DataFrame, today: date | None = None) -> int:
    """Consecutive days (ending today or yesterday) with a complete core check-in."""
    df = normalize(df)
    if df.empty:
        return 0
    today = today or date.today()
    per_day = df.groupby(df["ts"].dt.date)["indicator"].apply(set)
    complete = {d for d, inds in per_day.items() if set(CORE_INDICATORS) <= inds}
    cursor = today if today in complete else today - timedelta(days=1)
    n = 0
    while cursor in complete:
        n += 1
        cursor -= timedelta(days=1)
    return n


def _window(df: pd.DataFrame, end: date, days: int) -> pd.DataFrame:
    start = end - timedelta(days=days - 1)
    d = df[(df["ts"].dt.date >= start) & (df["ts"].dt.date <= end)]
    return d.assign(date=d["ts"].dt.date)


def _adherence(win: pd.DataFrame, end: date, days: int, today: date, now: datetime) -> tuple[int, int]:
    """(tasks done, tasks planned). Today only counts tasks whose time has come."""
    done = planned = 0
    per_day = win.groupby("date")["indicator"].apply(set) if not win.empty else {}
    for k in range(days):
        day = end - timedelta(days=k)
        logged = per_day.get(day, set()) if len(win) else set()
        for t in DAILY_TASKS:
            if day == today and now.hour < t["hour"] and not set(t["indicators"]) <= logged:
                continue  # not due yet
            planned += 1
            done += set(t["indicators"]) <= logged
    return done, planned


def _rating(ratio: float, good: float, fair: float) -> str:
    return GREEN if ratio >= good else YELLOW if ratio >= fair else RED


def weekly_review(
    df: pd.DataFrame,
    environment: str = DEFAULT_ENVIRONMENT,
    today: date | None = None,
    now: datetime | None = None,
) -> dict:
    """How the last 7 days went, habit by habit, plus the one thing worth focusing on."""
    from app.core.thresholds import green_range

    now = now or datetime.now()
    today = today or now.date()
    df = normalize(df)
    win = _window(df, today, REVIEW_DAYS)
    prev = _window(df, today - timedelta(days=REVIEW_DAYS), REVIEW_DAYS)

    done, planned = _adherence(win, today, REVIEW_DAYS, today, now)
    p_done, p_planned = _adherence(prev, today - timedelta(days=REVIEW_DAYS), REVIEW_DAYS, today, now)
    adherence = done / planned if planned else 0.0
    prev_adherence = p_done / p_planned if p_planned and not prev.empty else None

    def daily(ind: str) -> pd.Series:
        sub = win[win["indicator"] == ind]
        return sub.groupby("date")["value"].mean() if not sub.empty else pd.Series(dtype=float)

    sleep = daily("sleep_hours")
    ex = daily("exercise_minutes")
    ex_target = green_range("exercise_minutes", environment)[0]
    sleep_ok = int((sleep >= SLEEP_TARGET_H).sum())
    ex_ok = int((ex >= ex_target).sum())
    per_day = win.groupby("date")["indicator"].apply(set) if not win.empty else pd.Series(dtype=object)
    full_days = int(sum(set(CORE_INDICATORS) <= s for s in per_day))

    habits = [
        {"id": "measurements", "label": "Measurements taken", "value": done, "target": planned,
         "ratio": adherence, "status": _rating(adherence, ADHERENCE_GOOD, ADHERENCE_FAIR),
         "detail": f"{done} of {planned} planned measurements",
         "goal": "Aim for at least 80% — that's when the trends become reliable."},
        {"id": "sleep", "label": "Nights with 7+ hours of sleep", "value": sleep_ok, "target": REVIEW_DAYS,
         "ratio": sleep_ok / REVIEW_DAYS, "status": _rating(sleep_ok, DAYS_GOAL, 3),
         "detail": f"{sleep_ok} of {REVIEW_DAYS} nights"
                   + (f" · average {sleep.mean():.1f} h" if len(sleep) else ""),
         "goal": "Adults need at least 7 hours. Aim for 5 or more good nights a week."},
        {"id": "exercise", "label": f"Days with {ex_target:g}+ min of exercise", "value": ex_ok,
         "target": REVIEW_DAYS, "ratio": ex_ok / REVIEW_DAYS, "status": _rating(ex_ok, DAYS_GOAL, 3),
         "detail": f"{ex_ok} of {REVIEW_DAYS} days" + (f" · average {ex.mean():.0f} min" if len(ex) else ""),
         "goal": "Daily exercise is the main protection for bones and muscles. Aim for 5+ days."},
        {"id": "checkins", "label": "Days with a full check-in", "value": full_days, "target": REVIEW_DAYS,
         "ratio": full_days / REVIEW_DAYS, "status": _rating(full_days, DAYS_GOAL, 3),
         "detail": f"{full_days} of {REVIEW_DAYS} days",
         "goal": "A complete set of numbers on most days makes problems easy to spot early."},
    ]
    focus = None
    weakest = min(habits, key=lambda h: (SEVERITY[h["status"]] * -1, h["ratio"]))
    if weakest["status"] != GREEN:
        focus = {
            "measurements": "Your measurements have gaps. Keep the kit where you wake up, so morning vitals "
                            "take two minutes before anything else.",
            "sleep": "Sleep is the weak spot this week. Protect a fixed 8-hour sleep window and use the eye "
                     "mask and earplugs.",
            "exercise": "Exercise has slipped. Book it at the same time each day, like any other task on "
                        "the schedule.",
            "checkins": "Several days are missing a full check-in. The evening mood and dosimeter entries "
                        "are the ones most often forgotten.",
        }[weakest["id"]]
    trend = None
    if prev_adherence is not None:
        diff = adherence - prev_adherence
        trend = "steady" if abs(diff) < 0.05 else ("better" if diff > 0 else "worse")
    return {
        "days": REVIEW_DAYS,
        "start": today - timedelta(days=REVIEW_DAYS - 1),
        "end": today,
        "habits": habits,
        "adherence": adherence,
        "prev_adherence": prev_adherence,
        "trend": trend,
        "focus": focus,
        "consistency_days": streak_days(df, today),
    }


# --------------------------------------------------------- downlink --
def downlink_report(
    astronaut_id: str,
    environment: str,
    statuses: dict[str, IndicatorStatus],
    alerts: list[TrendAlert],
    recs: list[Recommendation],
    cumulative_dose_msv: float,
) -> str:
    """Compact Markdown summary to send to the flight surgeon at the next comm pass."""
    from app.core.status import needs_flight_surgeon  # local: avoid cycles

    icon = {GREEN: "[ok]", YELLOW: "[~]", RED: "[!]", UNKNOWN: "[ ]"}
    o = companion_overall(statuses, alerts)
    escalate, reasons = needs_flight_surgeon(statuses, alerts)
    lines = [
        f"# Caretta health downlink — {astronaut_id}",
        f"Generated {datetime.now():%Y-%m-%d %H:%M} · environment: {environment}",
        "",
        f"**Overall: {icon[o.status]} {o.label}**"
        + ("  — **care team looped in**" if escalate else ""),
        "",
        "| Indicator | Latest | Status | Time |",
        "|---|---|---|---|",
    ]
    for s in statuses.values():
        ind = INDICATORS[s.indicator]
        ts = s.ts[:16].replace("T", " ") if s.ts else "—"
        lines.append(f"| {ind.name} | {ind.format(s.value)} | {icon[s.status]} {status_label(s.status, s.indicator)} | {ts} |")
    lines += ["", f"Cumulative mission dose: **{cumulative_dose_msv:.1f} mSv**", ""]
    if reasons:
        lines += ["## Escalation reasons", *[f"- {r}" for r in reasons], ""]
    if alerts:
        lines += ["## Trend alerts", *[f"- {icon[a.status]} {a.title}" for a in alerts], ""]
    if recs:
        lines += ["## Actions taken / advised on board"]
        for r in recs:
            lines.append(f"- {icon[r.status]} **{r.title}** → {r.actions[0]}")
    return "\n".join(lines)
