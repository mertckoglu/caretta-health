"""Animated particle body map.

A custom Streamlit component (``app/ui/particle_body/index.html``, plain
HTML + Canvas, no build step) draws the human body with ~6–14k particles.
Selecting a body system makes the particles scatter and re-assemble into
that system (brain, heart, lungs, abdominal organs, lymphatic system,
skeleton, radiation view). Clicks are sent back to Python.

Performance notes (see the JS file): particles live in typed arrays, are
rasterised straight into one ImageData buffer with additive blending, the
glow is a 1/4-resolution down/up-scale, the idle animation runs at ~30 fps
and rendering pauses when the frame is hidden or off-screen.
"""
from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

from app.core.indicators import REGIONS
from app.core.thresholds import NEEDS_CARE, RED, STATUS_LABELS, UNKNOWN, worst
from app.ui.charts import STATUS_COLORS, STATUS_ICONS

COMPONENT_DIR = Path(__file__).resolve().parent / "particle_body"

SHORT_NAMES = {
    "brain": "Brain",
    "lungs": "Lungs",
    "heart": "Heart",
    "metabolism": "Metabolism",
    "immune": "Immune",
    "musculoskeletal": "Bones & muscle",
    "whole_body": "Radiation",
}
REGION_ORDER = list(SHORT_NAMES)
OVERVIEW = "overview"

_component = components.declare_component("caretta_particle_body", path=str(COMPONENT_DIR))


#: body systems whose problems build up slowly (sleep, mood, exercise): red there means "Needs care"
SLOW_REGIONS = {"brain", "musculoskeletal"}


def _status_payload(status: str, region: str | None = None, label: str | None = None) -> dict:
    if label is None:
        label = NEEDS_CARE if status == RED and region in SLOW_REGIONS else STATUS_LABELS[status]
    return {"status": status, "color": STATUS_COLORS[status], "icon": STATUS_ICONS[status], "label": label}


def region_payload(region_statuses: dict[str, str]) -> list[dict]:
    """Serializable description of every body system for the component."""
    return [
        {
            "key": key,
            "name": REGIONS[key]["name"],
            "short": SHORT_NAMES[key],
            **_status_payload(region_statuses.get(key, UNKNOWN), key),
        }
        for key in REGION_ORDER
    ]


def _overall_payload(region_statuses: dict[str, str]) -> dict:
    status = worst(region_statuses.values())
    reds = [r for r, st in region_statuses.items() if st == RED]
    label = NEEDS_CARE if reds and all(r in SLOW_REGIONS for r in reds) else STATUS_LABELS[status]
    return _status_payload(status, label=label)


def particle_body(view: str, region_statuses: dict[str, str], height: int = 660, key: str = "particle_body"):
    """Render the animated body. Returns ``{"view": str, "nonce": str}`` after a click, else ``None``."""
    return _component(
        view=view if view in REGIONS or view == OVERVIEW else OVERVIEW,
        regions=region_payload(region_statuses),
        overall=_overall_payload(region_statuses),
        height=height,
        key=key,
        default=None,
    )


# ----------------------------------------------------------------- section --
def _worst_region(region_statuses: dict[str, str]) -> str:
    from app.core.thresholds import SEVERITY

    ranked = sorted(REGION_ORDER, key=lambda k: -SEVERITY[region_statuses.get(k, UNKNOWN)])
    return ranked[0] if region_statuses.get(ranked[0]) in ("red", "yellow") else "heart"


def _show_trends(ctx, region: str) -> None:
    """Open a wide dialog with one full-size trend chart per indicator of ``region``."""
    import streamlit as st

    from app.core.indicators import indicators_for_region
    from app.ui.charts import indicator_chart

    @st.dialog(f"{REGIONS[region]['name']} · trends", width="large")
    def _dialog() -> None:
        for ind in indicators_for_region(region):
            st.plotly_chart(indicator_chart(ctx.df, ind.key, ctx.environment, height=380),
                            width="stretch", config={"displayModeBar": False}, key=f"chart_{ind.key}")

    _dialog()


def render_body_section(ctx, height: int = 620) -> None:
    """Particle body on the left, details of the selected body system on the right."""
    import streamlit as st

    from app.core import companion
    from app.core.companion import lc
    from app.core.indicators import indicators_for_region
    from app.core.recommend import recommend
    from app.ui import persistent_select
    from app.ui.charts import indicator_chart, status_chip
    from app.ui.icons import INDICATOR_ICONS, REGION_ICONS, icon

    ss = st.session_state
    ss.setdefault("_region", _worst_region(ctx.regions))
    ss.setdefault("_view", OVERVIEW)
    ss.setdefault("_pb_nonce", None)
    fig_col, info_col = st.columns([1.08, 1], gap="large")

    with fig_col:
        value = particle_body(ss["_view"], ctx.regions, height=height)
        if value and value.get("nonce") != ss["_pb_nonce"]:
            ss["_pb_nonce"] = value.get("nonce")
            ss["_view"] = value.get("view", OVERVIEW)
            if ss["_view"] != OVERVIEW:
                ss["_region"] = ss["_view"]
            st.rerun()
        # keyboard and screen-reader friendly alternative to the canvas
        persistent_select(
            "Body system", [OVERVIEW, *REGION_ORDER], "_view", "_w_body_view", widget=st.radio,
            format_func=lambda k: "Whole body" if k == OVERVIEW else REGIONS[k]["name"], horizontal=True,
        )
        if ss["_view"] != OVERVIEW:
            ss["_region"] = ss["_view"]

    region = ss["_region"]
    meta = REGIONS[region]
    status = ctx.regions[region]
    color = STATUS_COLORS[status]
    with info_col:
        label = NEEDS_CARE if status == RED and region in SLOW_REGIONS else None
        st.markdown(
            f"""<div class="ct-region__head" style="color:{color}">{icon(REGION_ICONS[region], 26)}
            <span>{meta['name']}</span></div>
            <div style="margin:.15rem 0 .7rem">{status_chip(status, text=label)}</div>
            <p class="ct-region__text">{meta['function']} <span>In space: {lc(meta['space_effects'])}</span></p>""",
            unsafe_allow_html=True,
        )
        # the numbers for this body system, as a flat list
        rows = []
        for ind in indicators_for_region(region):
            s = ctx.statuses[ind.key]
            rows.append(
                f"<li style='--c:{STATUS_COLORS[s.status]}'>{icon(INDICATOR_ICONS[ind.key], 18)}"
                f"<span class='ct-reading__name'>{ind.name}</span>"
                f"<span class='ct-reading__val'>{ind.format(s.value)}</span>{status_chip(s.status, indicator=ind.key)}</li>"
            )
        st.markdown(f"<ul class='ct-readings'>{''.join(rows)}</ul>", unsafe_allow_html=True)

        for a in [a for a in ctx.alerts if a.indicator in meta["indicators"]]:
            head, msg = companion.alert_text(a)
            st.warning(f"**{head}.** {msg}")

        # what to do — only for the readings that need it
        todo, looped = [], False
        for ind in indicators_for_region(region):
            s = ctx.statuses[ind.key]
            if s.status in ("yellow", "red"):
                rec = recommend(ind.key, s.value, s.status, ctx.environment)
                todo += rec.actions
                looped = looped or rec.escalate
        if todo:
            st.markdown("**What to do**  \n" + "\n".join(f"{n}. {a}" for n, a in enumerate(dict.fromkeys(todo), 1)))
            if looped:
                st.caption("Care team looped in. A short note goes out with the next downlink.")

        p1, p2 = st.columns(2)
        if p1.button("See the trends", width="stretch", key=f"trends_{region}"):
            _show_trends(ctx, region)
        with p2.popover("How to measure", width="stretch"):
            for ind in indicators_for_region(region):
                st.markdown(f"**{ind.name}.** {ind.how_to_measure}")
