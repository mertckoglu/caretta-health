"""Dynamic charts: how each indicator changes over the mission."""
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.core.indicators import INDICATORS  # noqa: E402
from app.core.status import cumulative_dose, daily_status_table, daily_table  # noqa: E402
from app.core.thresholds import CAREER_DOSE_LIMIT_MSV  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import dose_chart, indicator_chart, status_chip, status_heatmap  # noqa: E402

setup_page("Trends", "📈")
ctx = page_context()

st.title("📈 Trends")
if ctx.df.empty:
    st.info("No readings yet — do a check-in first.")
    st.stop()

span = st.segmented_control("Window", ["7 days", "14 days", "30 days", "All"], default="30 days")
days = {"7 days": 7, "14 days": 14, "30 days": 30}.get(span or "30 days")
df = ctx.df
if days:
    df = df[df["ts"] >= df["ts"].max().normalize() - timedelta(days=days - 1)]

st.subheader("Mission calendar")
st.caption("One square per day and indicator. Look for streaks of yellow/red — persistent deviations "
           "matter more than single readings.")
st.plotly_chart(status_heatmap(daily_status_table(df, ctx.environment)), width="stretch",
                config={"displayModeBar": False})

if ctx.alerts:
    st.subheader("Trend alerts")
    for a in ctx.alerts:
        st.markdown(f"{status_chip(a.status)} **{a.title}** — {a.message}", unsafe_allow_html=True)

st.subheader("Indicators")
chosen = st.multiselect(
    "Show",
    list(INDICATORS),
    default=["heart_rate", "systolic_bp", "sleep_hours", "mood", "body_temp", "exercise_minutes"],
    format_func=lambda k: INDICATORS[k].name,
)
cols = st.columns(2)
for i, key in enumerate(chosen):
    cols[i % 2].plotly_chart(indicator_chart(df, key, ctx.environment), width="stretch",
                             config={"displayModeBar": False}, key=f"trend_{key}")
st.caption("Shaded bands: green = nominal, yellow = watch, red = act. Dotted line = 7-day average.")

st.subheader("Radiation")
total = cumulative_dose(ctx.df)
c1, c2, c3 = st.columns(3)
c1.metric("Mission dose", f"{total:.1f} mSv")
c2.metric("Career limit used", f"{100 * total / CAREER_DOSE_LIMIT_MSV:.1f} %")
c3.metric("Career limit (NASA-STD-3001)", f"{CAREER_DOSE_LIMIT_MSV:.0f} mSv")
st.plotly_chart(dose_chart(df), width="stretch", config={"displayModeBar": False})

with st.expander("Raw daily averages"):
    table = daily_table(df).rename(columns={k: INDICATORS[k].name for k in INDICATORS})
    table.index = pd.to_datetime(table.index).date
    st.dataframe(table.round(2), width="stretch")
