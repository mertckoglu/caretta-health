"""Ground view: escalations, crew overview and a downlink report for the next comm pass."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.api import db  # noqa: E402
from app.core.indicators import INDICATORS  # noqa: E402
from app.core.recommend import downlink_report  # noqa: E402
from app.core.status import (  # noqa: E402
    cumulative_dose,
    detect_trends,
    evaluate_latest,
    needs_flight_surgeon,
    overall_status,
)
from app.core.thresholds import ENVIRONMENTS, STATUS_LABELS  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import STATUS_EMOJI, status_chip  # noqa: E402

setup_page("Flight surgeon", "📡")
ctx = page_context()

st.title("📡 Flight surgeon")
st.caption("When a result needs medical attention beyond self-care, Caretta packages the data for the "
           "crew medical officer and the flight surgeon on Earth.")

with st.expander("When does Caretta escalate?", expanded=False):
    st.markdown(
        "- any indicator in the **red** zone,\n"
        "- a **red trend** (e.g. 7+ days out of range, severe sleep debt, ≥ 80 % of career dose),\n"
        "- **three or more** indicators in the yellow zone at the same time.\n\n"
        f"Communication delay matters: in *{ENVIRONMENTS[ctx.environment]['label']}* the crew may have to act "
        "before ground can answer — the on-board guidance is written for that case."
    )

st.subheader(f"Crew overview — {ENVIRONMENTS[ctx.environment]['label']}")
rows = []
for member in db.list_astronauts(ctx.conn, ctx.environment):
    df = db.fetch_readings(ctx.conn, member, environment=ctx.environment)
    statuses = evaluate_latest(df, ctx.environment)
    alerts = detect_trends(df, ctx.environment)
    esc, reasons = needs_flight_surgeon(statuses, alerts)
    overall = overall_status(statuses, alerts)
    rows.append(
        {
            "Crew": member,
            "Overall": f"{STATUS_EMOJI[overall]} {STATUS_LABELS[overall]}",
            "Review": "📡 yes" if esc else "—",
            "Reasons": "; ".join(reasons) or "—",
            "Last reading": df["ts"].max().strftime("%Y-%m-%d %H:%M") if not df.empty else "—",
            "Mission dose (mSv)": round(cumulative_dose(df), 1),
        }
    )
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.subheader(f"Report for {ctx.astronaut}")
if ctx.df.empty:
    st.info("No data for this crew member yet.")
    st.stop()

if ctx.escalate:
    st.error("Review requested: " + "; ".join(ctx.reasons), icon="🚨")
else:
    st.success("No escalation criteria met.", icon="✅")

report = downlink_report(ctx.astronaut, ctx.environment, ctx.statuses, ctx.alerts, ctx.recs, cumulative_dose(ctx.df))
tab_report, tab_notes, tab_photos, tab_raw = st.tabs(["Downlink report", "Crew notes", "Photos", "Raw data"])
with tab_report:
    st.markdown(report)
    st.download_button("⬇️ Download report (.md)", report, file_name=f"caretta_{ctx.astronaut}_downlink.md",
                       mime="text/markdown")
with tab_notes:
    notes = ctx.df.dropna(subset=["note"]).drop_duplicates(subset=["ts", "note"])
    if notes.empty:
        st.caption("No notes or photos logged.")
    for r in notes.sort_values("ts", ascending=False).itertuples():
        st.markdown(f"**{r.ts:%Y-%m-%d %H:%M}** — {r.note}")
with tab_photos:
    pics = db.fetch_photos(ctx.conn, ctx.astronaut, ctx.environment)
    if pics.empty:
        st.caption("No photos logged.")
    else:
        cols = st.columns(4)
        for i, row in enumerate(pics.head(12).to_dict("records")):
            with cols[i % 4]:
                st.image(str(db.thumb_path(ctx.conn, row["filename"])), width="stretch")
                st.caption(f"{row['ts']:%d %b %H:%M} · {db.PHOTO_CATEGORIES.get(row['category'], '')}"
                           + (f" — {row['caption']}" if row["caption"] else ""))
        st.page_link("pages/4_Gallery.py", label=f"All {len(pics)} photos in the Gallery", icon="🖼️")
with tab_raw:
    raw = ctx.df.copy()
    raw["indicator"] = raw["indicator"].map(lambda k: INDICATORS[k].name)
    st.dataframe(raw.drop(columns=["id"]).sort_values("ts", ascending=False), hide_index=True,
                 width="stretch")
    st.download_button("⬇️ Download CSV", ctx.df.to_csv(index=False), file_name=f"caretta_{ctx.astronaut}.csv",
                       mime="text/csv")

st.markdown("Legend: " + " ".join(status_chip(s) for s in STATUS_LABELS), unsafe_allow_html=True)
