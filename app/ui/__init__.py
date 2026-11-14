"""Streamlit UI package. ``page_context`` is the shared sidebar + data loader every page uses."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PageContext:
    conn: object
    astronaut: str
    environment: str
    df: pd.DataFrame
    statuses: dict = field(default_factory=dict)
    alerts: list = field(default_factory=list)
    recs: list = field(default_factory=list)
    regions: dict = field(default_factory=dict)
    overall: str = "unknown"
    escalate: bool = False
    reasons: list = field(default_factory=list)


def setup_page(title: str, icon: str = "🐢") -> None:
    import streamlit as st

    st.set_page_config(page_title=f"{title} · Caretta", page_icon=icon, layout="wide")
    st.markdown(
        """<style>
        .block-container {padding-top: 1.6rem;}
        div[data-testid="stMetricValue"] {font-size: 1.5rem;}
        </style>""",
        unsafe_allow_html=True,
    )


def _conn():
    import streamlit as st

    from app.api import db

    @st.cache_resource
    def _cached():
        return db.connect()

    return _cached()


def seed_demo(conn, environment: str = "iss") -> int:
    """(Re)generate the simulated 30-day crew mission for ONE environment. Other environments are untouched."""
    from app.api import db
    from app.core.simulate import simulate_crew

    db.delete_environment(conn, environment)
    return db.insert_dataframe(conn, simulate_crew(days=30, environment=environment))


def ensure_environment_data(conn, environment: str) -> bool:
    """Every environment is its own mission dataset; simulate it automatically the first time it is opened."""
    from app.api import db

    if db.count_readings(conn, environment) == 0:
        seed_demo(conn, environment)
        return True
    return False


def persistent_select(label: str, options: list, state_key: str, widget_key: str, widget=None, **kwargs):
    """Selectbox/radio whose value survives reruns *and* page switches without losing clicks.

    The source of truth is ``st.session_state[state_key]``. Before rendering, the widget's own
    key is re-seeded from it (needed after a page switch, when Streamlit drops widget state);
    a user change is copied back by the ``on_change`` callback, which runs before the script.
    """
    import streamlit as st

    ss = st.session_state
    if ss.get(state_key) not in options:
        ss[state_key] = options[0]
    ss[widget_key] = ss[state_key]

    def _sync():
        ss[state_key] = ss[widget_key]

    widget = widget or st.selectbox
    return widget(label, options, key=widget_key, on_change=_sync, **kwargs)


def page_context() -> PageContext:
    """Render the sidebar (astronaut, environment, demo data) and evaluate the data."""
    import streamlit as st

    from app.api import db
    from app.core.recommend import recommendations_for
    from app.core.status import (
        detect_trends,
        evaluate_latest,
        needs_flight_surgeon,
        overall_status,
        region_status,
    )
    from app.core.simulate import ENV_PROFILES
    from app.core.thresholds import DEFAULT_ENVIRONMENT, ENVIRONMENTS

    conn = _conn()
    ss = st.session_state

    with st.sidebar:
        st.markdown("## 🐢 Caretta")
        st.caption("Astronaut health self-assessment")

        # Widgets use a fixed key + on_change callback. Their default must NOT change between
        # reruns (that would recreate the widget and silently drop every second selection);
        # the persistent values live in "_environment"/"_astronaut" so they survive page switches.
        ss.setdefault("_environment", DEFAULT_ENVIRONMENT)
        environment = persistent_select(
            "Mission environment", list(ENVIRONMENTS), "_environment", "_w_environment",
            format_func=lambda k: ENVIRONMENTS[k]["label"],
        )
        if ensure_environment_data(conn, environment):
            st.toast(f"Simulated a 30-day {ENVIRONMENTS[environment]['label']} mission for the crew.", icon="🛰️")
        st.caption(ENVIRONMENTS[environment]["notes"])

        crew = db.list_astronauts(conn, environment) or ["CDR"]
        if ss.get("_astronaut") and ss["_astronaut"] not in crew and ss.get("_custom_astronaut") == ss["_astronaut"]:
            crew = [ss["_astronaut"], *crew]  # freshly added crew member without readings yet
        persistent_select("Crew member", crew, "_astronaut", "_w_astronaut")
        with st.expander("➕ Add crew member"):
            new = st.text_input("Call sign", max_chars=16, placeholder="e.g. MS3").strip().upper()
            if st.button("Add", disabled=not new):
                ss["_astronaut"] = ss["_custom_astronaut"] = new
                st.rerun()
        astronaut = ss["_astronaut"]

        with st.expander("Mission data"):
            st.caption(ENV_PROFILES.get(environment, {}).get("story", ""))
            st.caption("Each environment keeps its own dataset — readings you log are saved to the "
                       "environment selected above.")
            if st.button("Re-simulate this environment", type="secondary"):
                seed_demo(conn, environment)
                st.rerun()
        st.divider()
        st.caption("⚠️ Decision-support prototype. Follow mission medical procedures "
                   "and your flight surgeon's instructions.")

    df = db.fetch_readings(conn, astronaut, environment=environment)
    statuses = evaluate_latest(df, environment)
    alerts = detect_trends(df, environment)
    recs = recommendations_for(statuses, alerts, environment)
    escalate, reasons = needs_flight_surgeon(statuses, alerts)
    return PageContext(
        conn=conn,
        astronaut=astronaut,
        environment=environment,
        df=df,
        statuses=statuses,
        alerts=alerts,
        recs=recs,
        regions=region_status(statuses, alerts),
        overall=overall_status(statuses, alerts),
        escalate=escalate,
        reasons=reasons,
    )
