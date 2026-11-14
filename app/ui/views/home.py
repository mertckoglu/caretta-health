"""Home: a personal greeting, the living body map, and what matters today. Nothing more."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.core import companion  # noqa: E402
from app.core.recommend import task_progress  # noqa: E402
from app.core.thresholds import GREEN, UNKNOWN  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.body_map import render_body_section  # noqa: E402
from app.ui.charts import STATUS_COLORS, status_chip  # noqa: E402
from app.ui.icons import icon  # noqa: E402
from app.ui.intro import render_intro_once  # noqa: E402

setup_page("Home")
render_intro_once()
ctx = page_context()

WHO = {
    "self": "You can handle this one yourself.",
    "crew medical officer": "Worth mentioning to your CMO today.",
    "flight surgeon": "Care team looped in.",
}


def section(title: str, ico: str) -> None:
    st.markdown(f"<div class='ct-section'>{icon(ico, 22)}<span>{title}</span></div>", unsafe_allow_html=True)


def link(page: str, label: str) -> None:
    try:
        st.page_link(page, label=label)
    except Exception:  # page registry not available when the view runs on its own (tests)
        pass


# ------------------------------------------------------------------ hello
o = companion.overall(ctx.statuses, ctx.alerts)
st.markdown(
    f"""<section class="ct-hero" style="--accent:{STATUS_COLORS[o.status]}">
      <h1 class="ct-hero__hello">{companion.greeting(ctx.astronaut)}</h1>
      <p class="ct-hero__lead">{companion.day_summary(ctx.statuses, ctx.alerts)}</p>
      <div class="ct-hero__status"><span class="ct-hero__dot"></span><b>{o.label}</b><span>{o.hint}</span></div>
    </section>""",
    unsafe_allow_html=True,
)
notes = st.container()   # fixed slot: keeps the body map at the same position whether or not notes show
if note := companion.missed_checkin(ctx.df):
    notes.info(note)
if ctx.escalate:
    reasons = companion.care_reasons(ctx.statuses, ctx.alerts)
    said = ", and ".join(reasons) if len(reasons) < 3 else ", ".join(reasons[:-1]) + ", and " + reasons[-1]
    notes.markdown(
        f"""<div class="ct-care"><div class="ct-care__title">{icon("stethoscope", 18)} Care team looped in</div>
        <p>We've noticed that {said}. A short report for your flight surgeon is ready and goes out with the next
        downlink. You don't need to do anything extra, and you can read exactly what it says on the Care team
        page.</p></div>""",
        unsafe_allow_html=True,
    )

# -------------------------------------------------------------- body map
render_body_section(ctx)

# ------------------------------------------------------- today, simply
st.markdown("<div class='ct-gap'></div>", unsafe_allow_html=True)
left, right = st.columns([1.6, 1], gap="large")
with left:
    section("What would help today", "sparkle")
    actionable = [r for r in ctx.recs if r.status not in (GREEN, UNKNOWN)]
    if not actionable:
        st.markdown("<p class='ct-quiet'>Nothing needs doing right now. Enjoy the view.</p>", unsafe_allow_html=True)
    items = "".join(
        f"<li><div>{status_chip(r.status, indicator=r.indicator)}</div><b>{r.title}</b>"
        f"<span>{r.actions[0]}</span><small>{WHO.get(r.contact, r.contact)}</small></li>"
        for r in actionable[:3]
    )
    if items:
        st.markdown(f"<ol class='ct-steps'>{items}</ol>", unsafe_allow_html=True)
    link("pages/1_Diagnosis.py", "Not feeling right? Answer a few questions")

with right:
    section("Today", "clock")
    tasks = task_progress(ctx.df)
    mark = {"done": (icon("check", 16), "ct-task--done"), "due": (icon("dot", 16), "ct-task--due"),
            "upcoming": ("", "ct-task--later")}
    rows = "".join(
        f"<li class='{mark[t['state']][1]}'><span class='ct-task__time'>{t['hour']:02d}:00</span>"
        f"<span class='ct-task__label'>{t['label']}</span><span class='ct-task__mark'>{mark[t['state']][0]}</span></li>"
        for t in tasks
    )
    st.markdown(f"<ul class='ct-tasks'>{rows}</ul>", unsafe_allow_html=True)
    due = [t for t in tasks if t["state"] == "due"]
    st.caption(f"{sum(t['state'] == 'done' for t in tasks)} of {len(tasks)} done today"
               + (f", {len(due)} waiting whenever you're ready" if due else ""))
    if due:
        link("pages/1_Check_In.py", "Go to check-in")
    link("views/progress.py", "Your week and mission patches")
