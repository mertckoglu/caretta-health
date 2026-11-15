"""Ground view: escalations, crew overview and a downlink report for the next comm pass."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.api import db  # noqa: E402
from app.core import companion  # noqa: E402
from app.core.diagnosis import URGENCY  # noqa: E402
from app.core.indicators import INDICATORS  # noqa: E402
from app.core.recommend import downlink_report  # noqa: E402
from app.core.status import (  # noqa: E402
    cumulative_dose,
    detect_trends,
    evaluate_latest,
    needs_flight_surgeon,
)
from app.core.thresholds import ENVIRONMENTS  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import status_legend  # noqa: E402

setup_page("Flight surgeon")
ctx = page_context()

st.title("Your care team")
st.caption("Everything the medical team on the ground needs in one place: who might need a call, a short "
           "report to send, notes, photos and saved assessments.")

with st.expander("When do we suggest calling the flight surgeon?", expanded=False):
    st.markdown(
        "We suggest it when:\n"
        "- any measurement is in the red zone,\n"
        "- something has been off for a week or more, sleep has been very short for days, or radiation is "
        "close to the career limit,\n"
        "- three or more measurements are in the yellow zone at the same time.\n\n"
        f"From {ENVIRONMENTS[ctx.environment]['label'].lower()}, an answer from Earth may take a while, so the "
        "advice in Caretta is written so you can act on it yourself first."
    )

st.subheader(f"Crew overview — {ENVIRONMENTS[ctx.environment]['label']}")
rows = []
for member in db.list_astronauts(ctx.conn, ctx.environment):
    df = db.fetch_readings(ctx.conn, member, environment=ctx.environment)
    statuses = evaluate_latest(df, ctx.environment)
    alerts = detect_trends(df, ctx.environment)
    esc, reasons = needs_flight_surgeon(statuses, alerts)
    rows.append(
        {
            "Crew": member,
            "Overall": companion.overall(statuses, alerts).label,
            "Care team": "Looped in" if esc else "—",
            "Reasons": "; ".join(reasons) or "—",
            "Last reading": df["ts"].max().strftime("%Y-%m-%d") if not df.empty else "—",
            "Mission dose (mSv)": round(cumulative_dose(df), 1),
        }
    )
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

st.subheader(f"Report for {ctx.astronaut}")
if ctx.df.empty:
    st.info("No data for this crew member yet.")
    st.stop()

if ctx.escalate:
    st.info("**Care team looped in.** For the medical team: " + "; ".join(ctx.reasons) + ".")
else:
    st.success("Smooth sailing. Nothing here needs the flight surgeon right now.")

report = downlink_report(ctx.astronaut, ctx.environment, ctx.statuses, ctx.alerts, ctx.recs, cumulative_dose(ctx.df))
tab_report, tab_dx, tab_notes, tab_photos, tab_raw = st.tabs(["Report", "Assessments", "Notes", "Photos", "All readings"])
with tab_report:
    st.markdown(report)
    st.download_button("Download report", report, file_name=f"caretta_{ctx.astronaut}_downlink.md",
                       mime="text/markdown")
with tab_dx:
    dx = db.fetch_diagnoses(ctx.conn, ctx.astronaut, ctx.environment)
    if dx.empty:
        st.caption("No saved assessments. They appear here when the crew member saves one on the Diagnosis page.")
    for row in dx.head(10).to_dict("records"):
        u = URGENCY.get(row["urgency"], URGENCY["self"])
        st.markdown(f"**{row['ts']:%d %b %H:%M}** · {row['title']} · "
                    f"<span style='color:{u['color']};font-weight:600'>{u['label']}</span>", unsafe_allow_html=True)
        with st.expander("Answers and advice"):
            d = row["details"]
            st.markdown("\n".join(f"- {a['question']} → **{a['answer']}**" for a in d.get("answers", [])))
            st.markdown("\n".join(f"{i}. {a}" for i, a in enumerate(d.get("actions", []), 1)))
with tab_notes:
    notes = ctx.df.dropna(subset=["note"]).drop_duplicates(subset=["ts", "note"])
    if notes.empty:
        st.caption("No notes yet.")
    for r in notes.sort_values("ts", ascending=False).itertuples():
        st.markdown(f"**{r.ts:%Y-%m-%d}** — {r.note}")
with tab_photos:
    pics = db.fetch_photos(ctx.conn, ctx.astronaut, ctx.environment)
    if pics.empty:
        st.caption("No photos yet.")
    else:
        cols = st.columns(4)
        for i, row in enumerate(pics.head(12).to_dict("records")):
            with cols[i % 4]:
                st.image(str(db.thumb_path(ctx.conn, row["filename"])), width="stretch")
                st.caption(f"{row['ts']:%d %b %H:%M} · {db.PHOTO_CATEGORIES.get(row['category'], '')}"
                           + (f" — {row['caption']}" if row["caption"] else ""))
        st.page_link("pages/4_Gallery.py", label=f"See all {len(pics)} in the Gallery")
with tab_raw:
    raw = ctx.df.copy()
    raw["indicator"] = raw["indicator"].map(lambda k: INDICATORS[k].name)
    st.dataframe(raw.drop(columns=["id"]).sort_values("ts", ascending=False), hide_index=True,
                 width="stretch")
    st.download_button("Download as CSV", ctx.df.to_csv(index=False), file_name=f"caretta_{ctx.astronaut}.csv",
                       mime="text/csv")

st.divider()
st.markdown(status_legend(), unsafe_allow_html=True)
