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

setup_page("About", "ℹ️")
ctx = page_context()

st.title("ℹ️ About Caretta")
st.markdown(
    "Like the loggerhead sea turtle (*Caretta caretta*) that carries its shelter on long journeys, "
    "**Caretta** gives astronauts a self-assessment tool they carry far from Earth: measure, understand, act, "
    "and know when to call the flight surgeon."
)

st.subheader("The five hazards of human spaceflight (NASA HRP)")
cols = st.columns(5)
for col, (key, h) in zip(cols, HAZARDS.items()):
    with col.container(border=True):
        st.markdown(f"### {h['icon']}\n**{h['name']}**")
        st.caption(h["summary"])
        affected = [i.name for i in INDICATORS.values() if key in i.hazards]
        st.markdown("Watched via: " + ", ".join(affected))


def _fmt(bands):
    return ", ".join(f"{lo:g}–{'∞' if hi == float('inf') else f'{hi:g}'}" for lo, hi in bands)


st.subheader(f"Thresholds — {ENVIRONMENTS[ctx.environment]['label']}")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Indicator": i.name,
                "Unit": i.unit,
                "🟢 Nominal": _fmt(get_thresholds(k, ctx.environment)["green"]),
                "🟡 Watch": _fmt(get_thresholds(k, ctx.environment)["yellow"]),
                "🔴 Act": "anything else",
            }
            for k, i in INDICATORS.items()
        ]
    ),
    hide_index=True,
    width="stretch",
)
st.caption("Screening limits for healthy, medically-selected adults; intervals are [low, high). "
           "Sources: data/thresholds_sources.md.")

st.subheader("Measurement guide")
for i in INDICATORS.values():
    with st.expander(f"{i.name} ({i.unit})"):
        st.markdown(f"**How to measure:** {i.how_to_measure}")
        st.markdown(f"**Why it matters:** {i.why_it_matters}")

st.subheader("Important")
st.warning(
    "Caretta is a hackathon prototype for decision support and education. It is not a medical device and "
    "does not diagnose. Always follow mission medical procedures and your flight surgeon's instructions.",
    icon="⚠️",
)
