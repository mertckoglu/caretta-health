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
from app.core.thresholds import STATUS_LABELS, UNKNOWN, worst
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


def _status_payload(status: str) -> dict:
    return {"status": status, "color": STATUS_COLORS[status], "icon": STATUS_ICONS[status], "label": STATUS_LABELS[status]}


def region_payload(region_statuses: dict[str, str]) -> list[dict]:
    """Serializable description of every body system for the component."""
    return [
        {
            "key": key,
            "name": REGIONS[key]["name"],
            "short": SHORT_NAMES[key],
            **_status_payload(region_statuses.get(key, UNKNOWN)),
        }
        for key in REGION_ORDER
    ]


def particle_body(view: str, region_statuses: dict[str, str], height: int = 660, key: str = "particle_body"):
    """Render the animated body. Returns ``{"view": str, "nonce": str}`` after a click, else ``None``."""
    return _component(
        view=view if view in REGIONS or view == OVERVIEW else OVERVIEW,
        regions=region_payload(region_statuses),
        overall=_status_payload(worst(region_statuses.values())),
        height=height,
        key=key,
        default=None,
    )
