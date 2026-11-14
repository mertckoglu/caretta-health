"""Caretta — mission health dashboard (entry point).

Run:  streamlit run app/ui/Home.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.core.indicators import INDICATORS  # noqa: E402
from app.core.recommend import badges, level_for, streak_days, task_progress, xp_total  # noqa: E402
from app.core.simulate import ENV_PROFILES  # noqa: E402
from app.core.status import completeness  # noqa: E402
from app.core.thresholds import ENVIRONMENTS, GREEN, UNKNOWN, classify, green_range  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import STATUS_COLORS, STATUS_EMOJI, overall_gauge, status_card, status_chip  # noqa: E402

setup_page("Mission health")
ctx = page_context()

BANNER = {
    "green": ("All systems nominal", "Keep up your routine — log your next check-in on time."),
    "yellow": ("Some indicators need watching", "Follow the guidance below and re-measure today."),
    "red": ("Action needed", "Follow the red guidance now and contact the crew medical officer."),
    "unknown": ("No data yet", "Start with a check-in to get your first assessment."),
}

title, sub = BANNER[ctx.overall]
color = STATUS_COLORS[ctx.overall]
st.markdown(
    f"""<div style="border-radius:14px;padding:18px 22px;background:{color}1f;border:2px solid {color};
    margin-bottom:14px"><div style="font-size:0.9rem;opacity:0.8">Crew member <b>{ctx.astronaut}</b></div>
    <div style="font-size:1.8rem;font-weight:800;color:{color}">{STATUS_EMOJI[ctx.overall]} {title}</div>
    <div>{sub}</div></div>""",
    unsafe_allow_html=True,
)
if ctx.escalate:
    st.error("**Flight surgeon review recommended:** " + "; ".join(ctx.reasons) +
             "  \n→ Open **Flight Surgeon** to prepare the downlink report.", icon="📡")

env = ENVIRONMENTS[ctx.environment]
with st.container(border=True):
    st.markdown(f"#### 🛰️ {env['label']}")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Gravity", f"{env['gravity_g']:g} g" if env["gravity_g"] else "Microgravity")
    lo, hi = env["one_way_delay_min"]
    e2.metric("Comm delay (one way)", "Live" if hi < 0.05 else f"{lo:g}–{hi:g} min",
              help="How long a message to the flight surgeon takes. Long delays → the crew must act on its own.")
    for col, key, label in ((e3, "radiation_dose", "Radiation target"), (e4, "exercise_minutes", "Exercise target")):
        ind = INDICATORS[key]
        g_lo, g_hi = green_range(key, ctx.environment)
        target = f"< {g_hi:g} {ind.unit}" if key == "radiation_dose" else f"≥ {g_lo:g} {ind.unit}"
        s_now = ctx.statuses[key]
        col.metric(label, target)
        if s_now.value is not None:
            col.markdown(f"Latest {ind.format(s_now.value)} {status_chip(s_now.status)}", unsafe_allow_html=True)
    st.caption(f"**Mission scenario:** {ENV_PROFILES[ctx.environment]['story']}  \n"
               "Every environment is its own mission: switching it loads (or simulates) that environment's data "
               "and applies its radiation, exercise and communication-delay rules.")

left, right = st.columns([3, 1.2], gap="large")

with left:
    st.subheader("Latest readings")
    keys = list(INDICATORS)
    for row in range(0, len(keys), 4):
        cols = st.columns(4)
        for col, key in zip(cols, keys[row : row + 4]):
            s = ctx.statuses[key]
            ind = INDICATORS[key]
            when = pd.Timestamp(s.ts).strftime("%d %b, %H:%M") if s.ts else "not measured yet"
            col.markdown(status_card(ind.name, ind.format(s.value), s.status, when), unsafe_allow_html=True)

    st.subheader("What to do now")
    actionable = [r for r in ctx.recs if r.status not in (GREEN, UNKNOWN)]
    if not actionable:
        st.success("Nothing to act on. Great job keeping your health on track! 🚀")
    for r in actionable[:5]:
        with st.container(border=True):
            st.markdown(f"{status_chip(r.status)} **{r.title}**", unsafe_allow_html=True)
            for a in r.actions:
                st.markdown(f"- {a}")
            st.caption(f"Who acts: {r.contact}")
    if len(actionable) > 5:
        st.caption(f"+{len(actionable) - 5} more on the Body Map and Flight Surgeon pages.")

with right:
    green_share = 100 * sum(s.status == GREEN for s in ctx.statuses.values()) / max(
        1, sum(s.status != UNKNOWN for s in ctx.statuses.values())
    )
    st.plotly_chart(overall_gauge(green_share), width="stretch",
                    config={"displayModeBar": False})
    st.caption(f"Data completeness: {100 * completeness(ctx.statuses):.0f}% of indicators reported")

    st.subheader("Today's routine")
    tasks = task_progress(ctx.df)
    icon = {"done": "✅", "due": "⏰", "upcoming": "🕒"}
    for t in tasks:
        st.markdown(f"{icon[t['state']]} **{t['hour']:02d}:00** {t['label']} "
                    f"<span style='opacity:.6'>+{t['xp']} XP</span>", unsafe_allow_html=True)
    due = [t for t in tasks if t["state"] == "due"]
    if due:
        st.page_link("pages/1_Check_In.py", label=f"Log {len(due)} due task(s) →", icon="📝")

    st.subheader("Progress")
    xp = xp_total(ctx.df)
    lv = level_for(xp)
    streak = streak_days(ctx.df)
    c1, c2 = st.columns(2)
    c1.metric("Level", lv["name"])
    c2.metric("Streak", f"{streak} 🔥" if streak else "0")
    st.progress(lv["progress"], text=f"{xp} XP" + (f" · {lv['next_xp'] - xp} to {lv['next_name']}" if lv["next_name"] else ""))
    earned = badges(ctx.df)
    st.markdown(
        " ".join(
            f"<span title='{b['name']}: {b['desc']}' style='font-size:1.6rem;"
            f"{'' if b['earned'] else 'filter:grayscale(1);opacity:.35'}'>{b['icon']}</span>"
            for b in earned
        ),
        unsafe_allow_html=True,
    )
    st.caption(f"{sum(b['earned'] for b in earned)}/{len(earned)} badges · hover to see how to earn them")

st.divider()
st.caption("Legend: " + " ".join(status_chip(s) for s in ("green", "yellow", "red", "unknown"))
           + " — shapes ●▲■ repeat the colour for colour-blind users.", unsafe_allow_html=True)
