"""Caretta's voice: how the app talks to the astronaut.

Everything here turns numbers and rules into the kind of sentence a doctor who
knows you would say. Rules of thumb used throughout:

* talk to the person, by role, and match the time of day;
* describe what happened, never blame ("you slept 5 hours", not "sleep: out of range");
* offer a next step and a choice ("want to try …, or should we send a note …?");
* a missed check-in is met with concern, not a penalty;
* milestones only ever add up — nothing is lost for a missed day.

The clinical wording (TrendAlert.title, needs_flight_surgeon reasons) stays as it
is for the medical team's reports; this module is for crew-facing screens.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from app.core.indicators import CORE_INDICATORS, INDICATORS
from app.core.status import IndicatorStatus, TrendAlert, normalize
from app.core.thresholds import (
    GREEN,
    NEEDS_CARE,
    RED,
    SEVERITY,
    SLOW_BUILDING,
    STATUS_HINTS,
    STATUS_LABELS,
    UNKNOWN,
    YELLOW,
    green_range,
)

ROLE_NAMES = {
    "CDR": "Commander",
    "PLT": "Pilot",
    "FE": "Flight Engineer",
    "MS": "Mission Specialist",
    "CMO": "Doctor",
}


def lc(name: str) -> str:
    """Lower-case a measurement name for use mid-sentence, keeping acronyms like SpO₂ intact."""
    return name[:1].lower() + name[1:] if name else name


def address(call_sign: str) -> str:
    """How we address someone: their role for standard call signs, otherwise the call sign itself."""
    cs = (call_sign or "").strip().upper()
    if cs in ROLE_NAMES:
        return ROLE_NAMES[cs]
    for prefix, role in ROLE_NAMES.items():
        if cs.startswith(prefix) and cs[len(prefix):].isdigit():
            return role
    return call_sign.strip() or "there"


def part_of_day(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "afternoon"
    if 18 <= h < 23:
        return "evening"
    return "night"


def greeting(call_sign: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    pod = part_of_day(now)
    hello = {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening",
             "night": "Still up"}[pod]
    return f"{hello}, {address(call_sign)}" + ("?" if pod == "night" else ".")


# ------------------------------------------------------------- overall mood --
@dataclass
class Overall:
    key: str        # smooth | shifting | needs_care | act_now | unknown
    status: str     # green / yellow / red / unknown (for colours)
    label: str
    hint: str


def overall(statuses: dict[str, IndicatorStatus], alerts: list[TrendAlert] | None = None) -> Overall:
    alerts = alerts or []
    items = [(s.indicator, s.status) for s in statuses.values()] + [(a.indicator, a.status) for a in alerts]
    worst = max((st for _, st in items), key=lambda st: SEVERITY[st], default=UNKNOWN)
    if worst == RED:
        acute = any(st == RED and ind not in SLOW_BUILDING for ind, st in items)
        if acute:
            return Overall("act_now", RED, STATUS_LABELS[RED], STATUS_HINTS[RED])
        return Overall("needs_care", RED, NEEDS_CARE, STATUS_HINTS[NEEDS_CARE])
    key = {GREEN: "smooth", YELLOW: "shifting", UNKNOWN: "unknown"}[worst]
    return Overall(key, worst, STATUS_LABELS[worst], STATUS_HINTS[worst])


# ------------------------------------------------------------ daily summary --
def _hours(h: float) -> str:
    whole = round(h * 2) / 2
    return f"{whole:g} hour" + ("" if whole == 1 else "s")


def _measured_today(s: IndicatorStatus | None, today: date) -> bool:
    return bool(s and s.value is not None and s.ts and pd.Timestamp(s.ts).date() == today)


def day_summary(
    statuses: dict[str, IndicatorStatus],
    alerts: list[TrendAlert] | None = None,
    now: datetime | None = None,
) -> str:
    """Two or three sentences about how today looks, in plain words."""
    now = now or datetime.now()
    today = now.date()
    pod = part_of_day(now)
    sleep, hr = statuses.get("sleep_hours"), statuses.get("heart_rate")
    parts = []
    if _measured_today(sleep, today):
        h = sleep.value
        if h < 6:
            parts.append(f"You only got {_hours(h)} of sleep last night")
        elif h >= 7:
            parts.append(f"You slept {_hours(h)} last night")
        else:
            parts.append(f"You slept {_hours(h)} last night, a little short of the 7 you need")
    if _measured_today(hr, today):
        parts.append(f"your resting heart rate is {hr.value:.0f}")
    if not parts:
        if pod in ("morning", "afternoon"):
            return "Whenever you're ready, a two-minute check-in will tell us how you're doing today."
        return "We haven't heard from you today. Would you like to do a quick check-in before you rest?"

    first = parts[0] + (f", and {parts[1]}" if len(parts) > 1 else "") + "."
    first = first[0].upper() + first[1:]
    o = overall(statuses, alerts)
    closing = {
        "smooth": {"morning": "You're starting the day well.",
                   "night": "Everything is looking steady. Try to get some rest soon."}.get(
                       pod, "Everything is looking steady today."),
        "shifting": "A couple of things are drifting a little. Nothing urgent; we'll look at them together below.",
        "needs_care": "Something needs a bit of care today. Let's take it one step at a time.",
        "act_now": "One reading needs attention right now. The steps are just below, and your care team is with you.",
        "unknown": "",
    }[o.key]
    return f"{first} {closing}".strip()


def missed_checkin(df: pd.DataFrame, today: date | None = None) -> str | None:
    """A gentle note if we haven't heard from someone. Never a penalty."""
    df = normalize(df)
    if df.empty:
        return None
    today = today or date.today()
    days = set(df["ts"].dt.date)
    if today in days:
        return None
    last = max(d for d in days if d < today) if any(d < today for d in days) else None
    if last is None:
        return None
    gap = (today - last).days
    if gap == 2:
        return "We missed you yesterday. Is everything okay?"
    if gap > 2:
        return (f"We haven't heard from you in {gap - 1} days. No pressure at all; just let us know "
                "you're okay when you have a moment.")
    return None


# ------------------------------------------------------------ trend alerts --
def alert_text(a: TrendAlert) -> tuple[str, str]:
    """(headline, message) for a trend alert, in the voice of someone on your side."""
    name = lc(INDICATORS[a.indicator].name)
    if a.kind == "persistent":
        n = int(a.value or 0)
        if a.indicator == "sleep_hours":
            return (f"You've slept below your target for {n} nights now",
                    "That must be tiring. Is there something you'd like to try, or should we send a note to "
                    "your flight surgeon?")
        if a.indicator == "mood":
            return (f"The last {n} days have felt heavy",
                    "That happens on long missions, and you don't have to carry it alone. Would a private call "
                    "with the behavioural health team help, or a chat with someone at home?")
        if a.indicator == "exercise_minutes":
            return (f"Exercise has been hard to fit in for {n} days",
                    "Busy days happen. Even a short session helps your bones and muscles. Want to block "
                    "out a fixed time tomorrow?")
        return (f"Your {name} has been off its usual range for {n} days",
                "One day on its own doesn't mean much, but a run of them is worth a closer look. Have a look "
                "at the suggestions below, or let your care team know if you'd like their view.")
    if a.kind == "sleep_debt":
        return (f"You've averaged {a.value:.1f} hours of sleep this week",
                "Your body is running on less rest than it needs. Protecting tonight's sleep is the kindest "
                "thing you can do for yourself right now. Want some ideas?")
    if a.kind == "hr_drift":
        return (f"Your resting heart rate has crept up about {a.value:.0f}%",
                "Compared with your first week. Often that's tiredness, a little dehydration or a cold "
                "coming on. Drink some water, check your temperature, and go easy on training today.")
    if a.kind == "low_mood":
        return ("The past few days seem to have been tough",
                "That's a normal part of long missions, and it's okay to say so. Would a call home or a quiet "
                "talk with the behavioural health team help?")
    if a.kind == "dose":
        return (f"You've built up {a.value:.0f} mSv of radiation so far",
                "Nothing to do today. Your flight surgeon will plan the rest of the mission with this in mind.")
    return a.title, a.message


def care_reasons(statuses: dict[str, IndicatorStatus], alerts: list[TrendAlert] | None = None) -> list[str]:
    """Why the care team was looped in, in plain words."""
    out = []
    for s in statuses.values():
        if s.status == RED:
            ind = INDICATORS[s.indicator]
            lo, hi = green_range(s.indicator)
            side = "low" if s.value < lo else "high"
            out.append(f"your {lc(ind.name)} is {side} at {ind.format(s.value)}")
    for a in alerts or []:
        if a.status == RED:
            out.append(alert_text(a)[0][0].lower() + alert_text(a)[0][1:])
    yellow = sum(1 for s in statuses.values() if s.status == YELLOW)
    if yellow >= 3:
        out.append(f"{yellow} readings are drifting at the same time")
    return out


# --------------------------------------------------------- mission patches --
@dataclass
class Patch:
    id: str
    title: str
    line: str          # what it means, in one calm sentence
    target: int
    count: int

    @property
    def earned(self) -> bool:
        return self.count >= self.target

    @property
    def to_go(self) -> int:
        return max(0, self.target - self.count)


def mission_patches(
    df: pd.DataFrame,
    environment: str = "iss",
    assessments: int = 0,
    photos: int = 0,
) -> list[Patch]:
    """Milestones that only ever add up. A missed day never takes anything away."""
    df = normalize(df)
    if df.empty:
        days_logged = full_days = rested = trained = 0
    else:
        d = df.assign(date=df["ts"].dt.date)
        per_day = d.groupby("date")["indicator"].apply(set)
        days_logged = len(per_day)
        full_days = int(sum(set(CORE_INDICATORS) <= s for s in per_day))
        daily = d.pivot_table(index="date", columns="indicator", values="value", aggfunc="mean")
        rested = int((daily.get("sleep_hours", pd.Series(dtype=float)) >= 7).sum())
        target = green_range("exercise_minutes", environment)[0]
        trained = int((daily.get("exercise_minutes", pd.Series(dtype=float)) >= target).sum())
    notes = int(df["note"].notna().sum()) if "note" in df else 0
    spoke_up = assessments + photos + notes
    return [
        Patch("first_light", "First Light", "Your first check-in. Welcome aboard.", 1, days_logged),
        Patch("first_week", "First Week", "You've checked in on 7 different days.", 7, days_logged),
        Patch("steady_hand", "Steady Hand", "You've been consistent for 30 days.", 30, full_days),
        Patch("deep_rest", "Deep Rest", "20 nights of 7 hours' sleep or more.", 20, rested),
        Patch("strong_frame", "Strong Frame", "20 days of countermeasure exercise done.", 20, trained),
        Patch("open_channel", "Open Channel", "You spoke up about how you feel. That takes courage.", 1,
              spoke_up),
    ]


def patch_progress_line(p: Patch) -> str:
    if p.earned:
        return p.line
    unit = {"deep_rest": "nights", "open_channel": ""}.get(p.id, "days")
    if p.id == "open_channel":
        return "Unlocks the first time you save a note, photo or assessment."
    return f"{p.to_go} more {unit[:-1] if p.to_go == 1 else unit} to go. No rush."


def consistency_line(df: pd.DataFrame) -> str | None:
    """Calm, cumulative wording — never a 'streak' that can be lost."""
    df = normalize(df)
    if df.empty:
        return None
    days = df["ts"].dt.date.nunique()
    return f"You've checked in on {days} day{'s' if days != 1 else ''} this mission."


__all__ = [
    "address", "greeting", "part_of_day", "overall", "Overall", "day_summary", "missed_checkin", "alert_text",
    "care_reasons", "Patch", "mission_patches", "patch_progress_line", "consistency_line",
]
