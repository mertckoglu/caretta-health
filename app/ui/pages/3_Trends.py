"""Dynamic charts: how each indicator changes over the mission."""
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.core import companion  # noqa: E402
from app.core.indicators import INDICATORS  # noqa: E402
from app.core.status import cumulative_dose, daily_status_table, daily_table  # noqa: E402
from app.core.thresholds import CAREER_DOSE_LIMIT_MSV  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import dose_chart, indicator_chart, status_card, status_chip, status_heatmap  # noqa: E402

setup_page("Trends")
ctx = page_context()

st.title("Trends")
if ctx.df.empty:
    st.info("Nothing to show yet. Your charts appear after your first check-in.")
    st.stop()

st.subheader("Your latest numbers")
_keys = list(INDICATORS)
for _row in range(0, len(_keys), 5):
    for _col, _key in zip(st.columns(5), _keys[_row:_row + 5]):
        _s = ctx.statuses[_key]
        _when = pd.Timestamp(_s.ts).strftime("%d %b, %H:%M") if _s.ts else "not measured yet"
        _col.markdown(status_card(INDICATORS[_key].name, INDICATORS[_key].format(_s.value), _s.status, _when,
                                  indicator=_key), unsafe_allow_html=True)

span = st.segmented_control("Show the last", ["7 days", "14 days", "30 days", "All"], default="30 days")
days = {"7 days": 7, "14 days": 14, "30 days": 30}.get(span or "30 days")
df = ctx.df
if days:
    df = df[df["ts"] >= df["ts"].max().normalize() - timedelta(days=days - 1)]

st.subheader("Day by day")
st.caption("Each square is one measurement on one day. A single yellow day is normal; a run of them is worth "
           "matter more than single readings.")
st.plotly_chart(status_heatmap(daily_status_table(df, ctx.environment)), width="stretch",
                config={"displayModeBar": False})

if ctx.alerts:
    st.subheader("Patterns we noticed")
    for a in ctx.alerts:
        head, msg = companion.alert_text(a)
        with st.container(border=True):
            st.markdown(f"{status_chip(a.status, indicator=a.indicator)} **{head}.**  \n{msg}", unsafe_allow_html=True)

st.subheader("Charts")
chosen = st.multiselect(
    "Measurements",
    list(INDICATORS),
    default=["heart_rate", "systolic_bp", "sleep_hours", "mood", "body_temp", "exercise_minutes"],
    format_func=lambda k: INDICATORS[k].name,
)
cols = st.columns(2)
for i, key in enumerate(chosen):
    cols[i % 2].plotly_chart(indicator_chart(df, key, ctx.environment), width="stretch",
                             config={"displayModeBar": False}, key=f"trend_{key}")
st.caption("Green band: smooth sailing. Yellow: shifting tides. Red: needs care or attention. "
           "The dotted line is your 7-day average.")

st.subheader("Radiation so far")
total = cumulative_dose(ctx.df)
c1, c2, c3 = st.columns(3)
c1.metric("This mission", f"{total:.1f} mSv")
c2.metric("Share of career limit", f"{100 * total / CAREER_DOSE_LIMIT_MSV:.1f}%")
c3.metric("NASA career limit", f"{CAREER_DOSE_LIMIT_MSV:.0f} mSv")
st.plotly_chart(dose_chart(df), width="stretch", config={"displayModeBar": False})

with st.expander("See the numbers"):
    table = daily_table(df).rename(columns={k: INDICATORS[k].name for k in INDICATORS})
    table.index = pd.to_datetime(table.index).date
    st.dataframe(table.round(2), width="stretch")
