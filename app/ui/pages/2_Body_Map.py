"""Clickable human figure: tap a body system to see its function, status and guidance."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.core.indicators import HAZARDS, REGIONS, indicators_for_region  # noqa: E402
from app.core.recommend import recommend  # noqa: E402
from app.core import companion  # noqa: E402
from app.core.thresholds import NEEDS_CARE, RED  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.body_map import OVERVIEW, REGION_ORDER, SLOW_REGIONS, particle_body  # noqa: E402
from app.ui.charts import indicator_chart, status_chip, status_legend  # noqa: E402

setup_page("Body map")
ctx = page_context()
ss = st.session_state

st.title("Body map")
st.caption("Click a part of the body, or pick one from the buttons under the figure, to see how it's doing "
           "and how spaceflight affects it. The coloured dots show your latest results.")

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
        format_func=lambda k: "Whole body" if k == OVERVIEW else REGIONS[k]["name"],
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
    region_label = NEEDS_CARE if status == RED and region in SLOW_REGIONS else None
    st.markdown(f"## {meta['name']} {status_chip(status, text=region_label)}", unsafe_allow_html=True)
    st.markdown(f"**What it does.** {meta['function']}")
    st.markdown(f"**What changes in space.** {meta['space_effects']}")
    hazards = sorted({h for ind in indicators_for_region(region) for h in ind.hazards})
    st.markdown("**Main causes.** " + ", ".join(HAZARDS[h]["name"].lower() for h in hazards).capitalize() + ".")

    for ind in indicators_for_region(region):
        s = ctx.statuses[ind.key]
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"**{ind.name}**  \n{status_chip(s.status, indicator=ind.key)}", unsafe_allow_html=True)
            c2.metric("Latest", ind.format(s.value), label_visibility="collapsed")
            rec = recommend(ind.key, s.value, s.status, ctx.environment)
            st.markdown(f"*{rec.title}*")
            for a in rec.actions:
                st.markdown(f"- {a}")
            if rec.escalate:
                st.info("Care team looped in. A short note for your flight surgeon goes out with the next downlink.")
            st.plotly_chart(indicator_chart(ctx.df, ind.key, ctx.environment, height=220),
                            width="stretch", config={"displayModeBar": False},
                            key=f"chart_{ind.key}")
            with st.expander("How to measure"):
                st.write(ind.how_to_measure)
                st.caption(ind.why_it_matters)

    related = [a for a in ctx.alerts if a.indicator in meta["indicators"]]
    for a in related:
        head, msg = companion.alert_text(a)
        st.warning(f"**{head}.** {msg}")

st.divider()
st.markdown(status_legend(), unsafe_allow_html=True)
