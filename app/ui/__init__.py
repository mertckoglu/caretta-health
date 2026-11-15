"""Streamlit UI package. ``page_context`` is the shared sidebar + data loader every page uses."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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


STATIC = Path(__file__).resolve().parent / "static"

# Caretta visual system — deep navy / indigo (never pure black), one warm accent (amber),
# Fraunces for headings, Inter for text and numbers, thin line icons (app/ui/icons.py).
# Motion: 0.3–0.6 s for everything except two ambient loops (breathing background, drifting stars);
# all of it switches off with prefers-reduced-motion.
THEME_CSS = """
<style>
:root {
  --ct-bg: #0b0f2a; --ct-bg2: #141a48; --ct-violet: #2a1f66; --ct-card: #151a42;
  --ct-line: #2c3570; --ct-text: #eceefb; --ct-muted: #a3a9d6; --ct-amber: #f5b041; --ct-amber-soft: #ffd48a;
  --ct-ease: cubic-bezier(.2,.7,.2,1);
}
@property --n { syntax: '<integer>'; inherits: false; initial-value: 0; }

/* calm background: one soft glow that barely breathes (6 s), a few static faint stars */
.stApp { background: var(--ct-bg); }
.stApp::before, .stApp::after { content:""; position:fixed; inset:0; pointer-events:none; z-index:0; }
.stApp::before {
  background:
    radial-gradient(60% 45% at 15% 0%, rgba(98,84,196,.13), transparent 65%),
    radial-gradient(50% 40% at 90% 10%, rgba(70,90,200,.10), transparent 65%),
    linear-gradient(180deg, #0b0f2a 0%, #0e1233 100%);
  animation: ct-breathe 6s ease-in-out infinite alternate;
}
.stApp::after {
  opacity:.18;
  background-image:
    radial-gradient(1px 1px at 12% 18%, #fff 50%, transparent 52%), radial-gradient(1px 1px at 32% 72%, #fff 50%, transparent 52%),
    radial-gradient(1px 1px at 58% 26%, #fff 50%, transparent 52%), radial-gradient(1px 1px at 76% 64%, #fff 50%, transparent 52%),
    radial-gradient(1px 1px at 88% 12%, #fff 50%, transparent 52%), radial-gradient(1px 1px at 6% 56%, #fff 50%, transparent 52%);
  background-size: 720px 720px;
}
@keyframes ct-breathe { from { opacity: .85; } to { opacity: 1; } }
[data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] { z-index: 1; background: transparent; }
[data-testid="stSidebar"] > div:first-child { background: #11153a; }

/* type */
.block-container {padding-top: 1.1rem; max-width: 1240px;}
h1, h2, h3, h4 { font-family: 'Fraunces', Georgia, serif !important; font-weight: 600 !important; letter-spacing: -0.01em; }
h1 { font-size: 2.4rem !important; }
p, li { line-height: 1.6; }
div[data-testid="stCaptionContainer"] { color: var(--ct-muted); }
div[data-testid="stMetricValue"] { font-size: 1.45rem; font-variant-numeric: tabular-nums; }
.ct-ico { vertical-align: -0.2em; flex: none; }

/* buttons & focus */
.stButton > button, .stDownloadButton > button { font-weight: 600; transition: transform .3s var(--ct-ease), background .3s, border-color .3s; }
.stButton > button:hover { transform: translateY(-1px); }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { color: #1d1400 !important; }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible, a:focus-visible, [role="tab"]:focus-visible
  { outline: 3px solid var(--ct-amber) !important; outline-offset: 3px; }
.stButton > button[kind="tertiary"] { border: 1px solid #ff7a7a; color: #ffb3b3; justify-content: flex-start; }
.stButton > button[kind="tertiary"]:hover { background: rgba(255,122,122,.12); color: #fff; }

/* soft entrance (0.5 s) */
@keyframes ct-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.ct-rise, .ct-hero, .ct-care, .ct-summary, .ct-patches, .ct-legend { animation: ct-rise .5s var(--ct-ease) both; }

/* count-up numbers (0.6 s) */
.ct-count { counter-reset: n var(--n); animation: ct-count .6s var(--ct-ease) both; font-variant-numeric: tabular-nums; }
.ct-count::before { content: counter(n); }
@keyframes ct-count { from { --n: 0; } }
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }

/* header */
.ct-header {display:flex; justify-content:space-between; align-items:center; gap:1rem; margin: 0 0 1.2rem;
  padding: .7rem 1rem; border-radius: .8rem; background: #131838;
  border: 1px solid var(--ct-line); box-shadow: inset 0 -2px 0 var(--ct-amber);}
.ct-header__brand {display:flex; align-items:center; gap:.55rem; color: var(--ct-amber);}
.ct-header__name {font-family:'Fraunces', Georgia, serif; font-weight:600; font-size:1.35rem; color:#fff; letter-spacing:-0.01em;}
.ct-header__tag {color: var(--ct-muted); font-size:.88rem;}
.ct-header__meta {color: var(--ct-text); font-size:.9rem; display:flex; align-items:center; gap:.4rem;}
.ct-header__meta .ct-ico {color: var(--ct-amber);}

/* home hero */
.ct-hero {position:relative; overflow:hidden; border:1px solid var(--ct-line); border-radius:1rem;
  padding:1.6rem 1.8rem 1.35rem; margin-bottom:1rem;
  background: radial-gradient(90% 120% at 100% 0%, color-mix(in srgb, var(--accent) 9%, transparent) 0%, transparent 55%), #141940;}
.ct-hero__hello {font-family:'Fraunces', Georgia, serif; font-weight:600; font-size:2.5rem; line-height:1.1;
  margin:0 0 .55rem; padding:0; letter-spacing:-0.02em; color:#fff;}
.ct-hero__lead {font-size:1.12rem; line-height:1.6; color:#dfe2fa; max-width:48rem; margin:0 0 1rem;}
.ct-hero__status {display:flex; align-items:center; gap:.6rem; flex-wrap:wrap; font-size:.95rem;}
.ct-hero__status b {color:var(--accent);}
.ct-hero__status span:last-child {color: var(--ct-muted);}
.ct-hero__dot {width:.65rem; height:.65rem; border-radius:50%; background:var(--accent); animation: ct-pulse 2.6s ease-out infinite;}
@keyframes ct-pulse {0% {box-shadow:0 0 0 0 color-mix(in srgb, var(--accent) 60%, transparent);} 80%,100% {box-shadow:0 0 0 .6rem transparent;}}

.ct-care {border:1px solid var(--ct-line); border-left:.25rem solid var(--ct-amber); background: #161a40;
  border-radius:.8rem; padding:.9rem 1.1rem; margin:0 0 1rem;}
.ct-care__title {font-weight:600; color: var(--ct-amber-soft); margin-bottom:.25rem; display:flex; gap:.45rem; align-items:center;}
.ct-care p {margin:0; color:#dfe2fa;}

.ct-section {display:flex; align-items:center; gap:.5rem; color: var(--ct-amber); margin:.4rem 0 .2rem;}
.ct-section span {font-family:'Fraunces', Georgia, serif; color: var(--ct-text); font-size:1.55rem; font-weight:600;}

/* cards */
.ct-card {border-radius:.8rem; padding:.8rem .9rem; background: var(--ct-card); border:1px solid var(--ct-line);
  margin-bottom:.6rem; min-height:126px; transition: border-color .3s, transform .3s var(--ct-ease); animation: ct-rise .5s var(--ct-ease) both;}
.ct-card:hover {transform: translateY(-2px); border-color: color-mix(in srgb, var(--accent) 70%, var(--ct-line));}
.ct-card__top {display:flex; align-items:center; gap:.45rem; font-size:.82rem; color: var(--ct-muted);}
.ct-card__top .ct-ico {color: var(--accent);}
.ct-card__value {font-size:1.6rem; font-weight:650; margin:.25rem 0 .3rem; letter-spacing:-0.01em; font-variant-numeric: tabular-nums;}
.ct-card__value small {font-size:.95rem; font-weight:500; color: var(--ct-muted); margin-left:.15rem;}
.ct-card__when {font-size:.72rem; color: var(--ct-muted); margin-top:.3rem;}

.ct-summary {background: var(--ct-card); border:1px solid var(--ct-line); border-radius:.8rem; padding:.8rem 1rem; color: var(--ct-muted); font-size:.9rem;}
.ct-summary__big {font-size:2rem; font-weight:650; color: var(--ct-text); line-height:1.1;}
.ct-summary__big .ct-den {font-size:1.1rem; color: var(--ct-muted); font-weight:400;}
.ct-tasks {list-style:none; padding:0; margin:.2rem 0 .3rem;}
.ct-tasks li {display:flex; gap:.7rem; align-items:center; padding:.45rem 0; border-bottom:1px solid rgba(44,53,112,.7); font-size:.93rem;}
.ct-task__time {color: var(--ct-muted); font-variant-numeric: tabular-nums; min-width:2.8rem;}
.ct-task__label {flex:1;}
.ct-task__mark {display:flex; color: var(--ct-muted);}
.ct-task--done .ct-task__label {color: var(--ct-muted); text-decoration: line-through; text-decoration-color: rgba(163,169,214,.5);}
.ct-task--done .ct-task__mark {color:#4fd1a5;}
.ct-task--due .ct-task__label {font-weight:600;}
.ct-task--due .ct-task__mark {color: var(--ct-amber);}
.ct-habit {margin:.15rem 0 .8rem;}
.ct-habit__row {display:flex; flex-direction:column; font-size:.92rem; margin-bottom:.35rem; line-height:1.3;}
.ct-habit__val {color: var(--ct-muted); font-size:.82rem;}
.ct-habit__bar {height:.4rem; background: rgba(44,53,112,.8); border-radius:.3rem; overflow:hidden;}
.ct-habit__bar div {height:100%; border-radius:.3rem; transition: width .6s var(--ct-ease);}
[data-testid="stSidebar"] h3 {margin-bottom: 0;}

.ct-legend {display:grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap:.5rem 1.4rem;}
.ct-legend__item {display:flex; flex-direction:column; gap:.25rem; font-size:.86rem; color:var(--ct-muted);}
.ct-patches {display:grid; grid-template-columns: repeat(auto-fill, minmax(6.4rem, 1fr)); gap:.9rem .6rem; margin:.4rem 0 .4rem;}
.ct-patch {margin:0; display:flex; flex-direction:column; align-items:center; text-align:center; gap:.35rem;}
.ct-patch svg {transition: transform .4s var(--ct-ease); filter: drop-shadow(0 .25rem .5rem rgba(5,7,30,.6));}
.ct-patch:hover svg {transform: rotate(-4deg) scale(1.04);}
.ct-patch figcaption {display:flex; flex-direction:column; font-size:.74rem; line-height:1.3; color:var(--ct-muted);}
.ct-patch figcaption b {color:var(--ct-text); font-size:.8rem;}
.ct-patch--locked figcaption b {color:var(--ct-muted); font-weight:600;}

/* body map side panel: flat, no nested boxes */
.ct-region__head {display:flex; align-items:center; gap:.55rem;}
.ct-region__head span {font-family:'Fraunces', Georgia, serif; font-size:1.7rem; font-weight:600; color: var(--ct-text);}
.ct-region__text {color:#d6daf5; font-size:.95rem; margin:0 0 .9rem;}
.ct-region__text span {display:block; color: var(--ct-muted); margin-top:.35rem; font-size:.9rem;}
.ct-readings {list-style:none; padding:0; margin:0 0 1rem; border-top:1px solid var(--ct-line);}
.ct-readings li {display:flex; align-items:center; gap:.6rem; padding:.65rem 0; border-bottom:1px solid var(--ct-line);}
.ct-readings li .ct-ico {color: var(--c);}
.ct-reading__name {flex:1;}
.ct-reading__val {font-weight:650; font-variant-numeric: tabular-nums; min-width:5.5rem; text-align:right;}

/* what would help today */
.ct-gap {height:.6rem;}
.ct-quiet {color: var(--ct-muted);}
.ct-steps {list-style:none; padding:0; margin:0 0 .8rem; counter-reset: step;}
.ct-steps li {display:grid; grid-template-columns: 1fr; gap:.2rem; padding:.8rem 0; border-bottom:1px solid var(--ct-line);}
.ct-steps li b {font-weight:600;}
.ct-steps li span {color:#d6daf5;}
.ct-steps li small {color: var(--ct-muted);}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
  .ct-intro, .ct-skip { display: none !important; }
}
</style>
"""


def setup_page(title: str, icon: str | None = None) -> None:
    import streamlit as st

    try:
        st.set_page_config(page_title=f"{title} · Caretta", page_icon=str(STATIC / "favicon.png"), layout="wide")
    except Exception:  # already set by the router in this run
        pass
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_header(astronaut: str, environment_label: str) -> None:
    import streamlit as st

    from app.ui.icons import icon

    st.markdown(
        f"""<div class="ct-header"><div class="ct-header__brand">{icon("patch", 22)}
        <span class="ct-header__name">Caretta</span><span class="ct-header__tag">your health companion</span></div>
        <div class="ct-header__meta">{icon("satellite", 16)} <b>{astronaut}</b> · {environment_label}</div></div>""",
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
        st.markdown("### Caretta")
        st.caption("Health checks for long missions")

        # Widgets use a fixed key + on_change callback. Their default must NOT change between
        # reruns (that would recreate the widget and silently drop every second selection);
        # the persistent values live in "_environment"/"_astronaut" so they survive page switches.
        ss.setdefault("_environment", DEFAULT_ENVIRONMENT)
        environment = persistent_select(
            "Where are you?", list(ENVIRONMENTS), "_environment", "_w_environment",
            format_func=lambda k: ENVIRONMENTS[k]["label"],
        )
        if ensure_environment_data(conn, environment):
            st.toast(f"No data for {ENVIRONMENTS[environment]['label']} yet, so we generated a 30-day practice mission.")
        st.caption(ENVIRONMENTS[environment]["notes"])

        crew = db.list_astronauts(conn, environment) or ["CDR"]
        if ss.get("_astronaut") and ss["_astronaut"] not in crew and ss.get("_custom_astronaut") == ss["_astronaut"]:
            crew = [ss["_astronaut"], *crew]  # freshly added crew member without readings yet
        persistent_select("Who's checking in?", crew, "_astronaut", "_w_astronaut")
        with st.expander("Add a crew member"):
            new = st.text_input("Call sign", max_chars=16, placeholder="e.g. MS3").strip().upper()
            if st.button("Add", disabled=not new, width="stretch"):
                ss["_astronaut"] = ss["_custom_astronaut"] = new
                st.rerun()
        astronaut = ss["_astronaut"]

        with st.expander("About this mission's data"):
            st.caption(ENV_PROFILES.get(environment, {}).get("story", ""))
            st.caption("Each location keeps its own records. Anything you log is saved under the location "
                       "selected above.")
            if st.button("Generate a new practice mission", type="secondary", width="stretch"):
                seed_demo(conn, environment)
                st.rerun()
        st.divider()
        st.caption("Caretta supports your judgement; it doesn't replace it. Mission medical procedures "
                   "and your flight surgeon always come first.")

    render_header(astronaut, ENVIRONMENTS[environment]["label"])
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