"""Learn: the five hazards, how indicators are measured and where thresholds come from."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app.core.indicators import HAZARDS, INDICATORS  # noqa: E402
from app.core.thresholds import ENVIRONMENTS, get_thresholds  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402

setup_page("About")
ctx = page_context()

st.title("About Caretta")
st.markdown(
    "Caretta is named after the loggerhead sea turtle, *Caretta caretta*, which carries its shelter with it "
    "on very long journeys. On a long mission there's no clinic down the hall, so astronauts need a quick, "
    "honest picture of their own health: what to measure, what the numbers mean, what to do about them, and "
    "when to call the flight surgeon. That's what this app is for."
)

st.subheader("What makes spaceflight hard on the body")
cols = st.columns(5)
for col, (key, h) in zip(cols, HAZARDS.items()):
    with col.container(border=True):
        st.markdown(f"**{h['name']}**")
        st.caption(h["summary"])
        affected = [i.name for i in INDICATORS.values() if key in i.hazards]
        st.caption("We track it with: " + ", ".join(a.lower() for a in affected) + ".")


def _fmt(bands):
    return ", ".join(f"{lo:g}–{'∞' if hi == float('inf') else f'{hi:g}'}" for lo, hi in bands)


st.subheader(f"Normal ranges: {ENVIRONMENTS[ctx.environment]['label']}")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Indicator": i.name,
                "Unit": i.unit,
                "Normal": _fmt(get_thresholds(k, ctx.environment)["green"]),
                "Keep an eye on": _fmt(get_thresholds(k, ctx.environment)["yellow"]),
                "Act": "Anything else",
            }
            for k, i in INDICATORS.items()
        ]
    ),
    hide_index=True,
    width="stretch",
)
st.caption("Screening limits for healthy, medically-selected adults; intervals are [low, high). "
           "Sources: data/thresholds_sources.md.")

st.subheader("How to take each measurement")
for i in INDICATORS.values():
    with st.expander(f"{i.name} ({i.unit})"):
        st.markdown(f"**How to measure:** {i.how_to_measure}")
        st.markdown(f"**Why it matters:** {i.why_it_matters}")

st.subheader("Design")
st.caption("Deep navy and indigo backgrounds with one warm amber accent, Fraunces for headings and Inter for "
           "text (both under the SIL Open Font License), and a small set of line icons drawn for Caretta. Animations "
           "stay between 0.3 and 0.6 seconds and switch off if your system asks for reduced motion. Caretta is a "
           "student project for the NASA Space Apps Challenge and is not an official NASA product.")

st.subheader("Please note")
st.warning(
    "Caretta was built for the NASA Space Apps Challenge. It is not a medical device. The Diagnosis page "
    "suggests likely explanations to help you decide what to do next, but it can't examine you. Mission medical "
    "procedures and your flight surgeon always come first.",
)
