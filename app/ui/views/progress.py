"""Your progress: how the week went, mission patches, and where you are."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.api import db  # noqa: E402
from app.core import companion  # noqa: E402
from app.core.indicators import INDICATORS  # noqa: E402
from app.core.recommend import weekly_review  # noqa: E402
from app.core.simulate import ENV_PROFILES  # noqa: E402
from app.core.thresholds import ENVIRONMENTS, green_range  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import STATUS_COLORS, status_legend  # noqa: E402
from app.ui.patches import patches_grid_html  # noqa: E402

setup_page("Your progress")
ctx = page_context()

st.title("Your progress")
st.caption("A calm look back: how the week went, the milestones you've reached, and the place you're in.")

week, patches_col = st.columns([1, 1.15], gap="large")
with week:
    review = weekly_review(ctx.df, ctx.environment)
    st.subheader("This week")
    st.caption(f"{review['start']:%d %b} – {review['end']:%d %b}")
    st.markdown("".join(
        f"<div class='ct-habit' title='{h['goal']}'><div class='ct-habit__row'><span>{h['label']}</span>"
        f"<span class='ct-habit__val'>{h['detail']}</span></div>"
        f"<div class='ct-habit__bar'><div style='width:{100 * min(h['ratio'], 1):.0f}%;"
        f"background:{STATUS_COLORS[h['status']]}'></div></div></div>"
        for h in review["habits"]), unsafe_allow_html=True)
    if review["trend"]:
        st.caption({"better": "Your measurements are more regular than last week.",
                    "worse": "A little less regular than last week. That's okay; this week is a fresh start.",
                    "steady": "About as regular as last week."}[review["trend"]])
    if review["focus"]:
        st.info(review["focus"])
    else:
        st.success("A solid week. Keep the same routine.")

with patches_col:
    st.subheader("Mission patches")
    patches = companion.mission_patches(
        ctx.df, ctx.environment,
        assessments=len(db.fetch_diagnoses(ctx.conn, ctx.astronaut, ctx.environment)),
        photos=len(db.fetch_photos(ctx.conn, ctx.astronaut, ctx.environment)),
    )
    if line := companion.consistency_line(ctx.df):
        st.caption(line)
    st.markdown(patches_grid_html([(p.id, p.title, p.earned, companion.patch_progress_line(p)) for p in patches],
                                  size=96), unsafe_allow_html=True)
    st.caption("Patches only ever add up. Missing a day never takes one away.")

env = ENVIRONMENTS[ctx.environment]
st.subheader(f"Where you are: {env['label']}")
e1, e2, e3, e4 = st.columns(4)
e1.metric("Gravity", f"{env['gravity_g']:g} g" if env["gravity_g"] else "Microgravity")
lo, hi = env["one_way_delay_min"]
e2.metric("Message delay to Earth", "None" if hi < 0.05 else f"{lo:g}–{hi:g} min")
rd, ex = INDICATORS["radiation_dose"], INDICATORS["exercise_minutes"]
e3.metric("Daily radiation limit", f"< {green_range('radiation_dose', ctx.environment)[1]:g} {rd.unit}")
e4.metric("Daily exercise goal", f"≥ {green_range('exercise_minutes', ctx.environment)[0]:g} {ex.unit}")
st.caption(ENV_PROFILES[ctx.environment]["story"])

st.divider()
st.markdown(status_legend(), unsafe_allow_html=True)
