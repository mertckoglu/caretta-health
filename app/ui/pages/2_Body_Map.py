"""Clickable human figure: tap a body system to see its function, status and guidance."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.core.indicators import HAZARDS, REGIONS, indicators_for_region  # noqa: E402
from app.core.recommend import recommend  # noqa: E402
from app.core.thresholds import STATUS_LABELS  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.body_map import OVERVIEW, REGION_ORDER, particle_body  # noqa: E402
from app.ui.charts import STATUS_EMOJI, indicator_chart, status_chip  # noqa: E402

setup_page("Body map", "🧍")
ctx = page_context()
ss = st.session_state

st.title("🧍 Body map")
st.caption("The body is drawn with thousands of particles, coloured by anatomy. Click a body system (or a chip "
           "below the figure): the particles scatter and re-assemble into that system. Status dots show your latest result.")

ss.setdefault("_region", "heart")
ss.setdefault("_view", OVERVIEW)
ss.setdefault("_pb_nonce", None)
fig_col, info_col = st.columns([1.1, 1], gap="large")

with fig_col:
    value = particle_body(ss["_view"], ctx.regions, height=720)
    if value and value.get("nonce") != ss["_pb_nonce"]:
        ss["_pb_nonce"] = value.get("nonce")
        new_view = value.get("view", OVERVIEW)
        ss["_view"] = new_view
        if new_view != OVERVIEW:
            ss["_region"] = new_view
        st.rerun()
    # Keyboard / screen-reader friendly alternative to the canvas
    options = [OVERVIEW, *REGION_ORDER]
    choice = st.radio(
        "Body system",
        options,
        index=options.index(ss["_view"]),
        format_func=lambda k: "🧍 Full body" if k == OVERVIEW else f"{STATUS_EMOJI[ctx.regions[k]]} {REGIONS[k]['name']}",
        horizontal=True,
    )
    if choice != ss["_view"]:
        ss["_view"] = choice
        if choice != OVERVIEW:
            ss["_region"] = choice
        st.rerun()

region = ss["_region"]
meta = REGIONS[region]
with info_col:
    status = ctx.regions[region]
    st.markdown(f"## {meta['name']} {status_chip(status)}", unsafe_allow_html=True)
    st.markdown(f"**What it does:** {meta['function']}")
    st.markdown(f"**In space:** {meta['space_effects']}")
    hazards = sorted({h for ind in indicators_for_region(region) for h in ind.hazards})
    st.markdown("**Driven by:** " + " · ".join(f"{HAZARDS[h]['icon']} {HAZARDS[h]['name']}" for h in hazards))

    for ind in indicators_for_region(region):
        s = ctx.statuses[ind.key]
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"**{ind.name}**  \n{status_chip(s.status)}", unsafe_allow_html=True)
            c2.metric("Latest", ind.format(s.value), label_visibility="collapsed")
            rec = recommend(ind.key, s.value, s.status, ctx.environment)
            st.markdown(f"*{rec.title}*")
            for a in rec.actions:
                st.markdown(f"- {a}")
            if rec.escalate:
                st.error(f"Escalate to the {rec.contact}.", icon="📡")
            st.plotly_chart(indicator_chart(ctx.df, ind.key, ctx.environment, height=220),
                            width="stretch", config={"displayModeBar": False},
                            key=f"chart_{ind.key}")
            with st.expander("How to measure"):
                st.write(ind.how_to_measure)
                st.caption(ind.why_it_matters)

    related = [a for a in ctx.alerts if a.indicator in meta["indicators"]]
    for a in related:
        st.warning(f"**Trend:** {a.title} — {a.message}", icon="📈")

st.caption("Status: " + ", ".join(f"{STATUS_EMOJI[k]} {v}" for k, v in STATUS_LABELS.items()))
