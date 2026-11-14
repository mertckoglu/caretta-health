"""Plotly charts and small HTML widgets shared by the Streamlit pages.

Status is never conveyed by colour alone: every chip also carries an icon
and a text label (colour-blind safe).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from app.core.indicators import INDICATORS
from app.core.status import daily_table
from app.core.thresholds import (
    GREEN,
    NEEDS_CARE,
    RED,
    STATUS_HINTS,
    STATUS_LABELS,
    UNKNOWN,
    YELLOW,
    classify,
    get_thresholds,
    status_label,
)

# Status colours: readable on deep navy and kept apart from the amber brand accent (#F5B041)
STATUS_COLORS = {GREEN: "#4FD1A5", YELLOW: "#EAD94C", RED: "#FF7A7A", UNKNOWN: "#9AA3C7"}
ACCENT = "#F5B041"
STATUS_ICONS = {GREEN: "●", YELLOW: "▲", RED: "■", UNKNOWN: "○"}
BAND_FILL = {GREEN: "rgba(79,209,165,0.12)", YELLOW: "rgba(234,217,76,0.11)", RED: "rgba(255,122,122,0.10)"}


def status_chip(status: str, text: str | None = None, indicator: str | None = None) -> str:
    color = STATUS_COLORS[status]
    label = text or status_label(status, indicator)
    return (
        f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
        f"background:{color}22;border:1px solid {color};color:{color};font-weight:600;"
        f"font-size:0.85rem;white-space:nowrap'>{STATUS_ICONS[status]} {label}</span>"
    )


def count_up(text: str) -> str:
    """Animate the leading whole number of ``text`` from 0 (CSS only, 0.6 s); the rest stays static.

    "36.6 °C" -> count 0→36, then ".6 °C". Screen readers get the plain text.
    """
    import re

    m = re.match(r"^(\d+)(.*)$", text or "")
    if not m:
        return text
    whole, rest = m.groups()
    return (f'<span aria-hidden="true"><span class="ct-count" style="--n:{int(whole)}"></span>{rest}</span>'
            f'<span class="sr-only">{text}</span>')


def status_card(title: str, value: str, status: str, subtitle: str = "", indicator: str | None = None) -> str:
    from app.ui.icons import INDICATOR_ICONS, icon

    color = STATUS_COLORS[status]
    num, _, unit = value.partition(" ")
    shown = count_up(num) + (f"<small>{unit}</small>" if unit else "")
    ico = icon(INDICATOR_ICONS.get(indicator, "circle"), 16)
    return f"""
    <div class="ct-card" style="--accent:{color}; box-shadow: inset 3px 0 0 {color};">
      <div class="ct-card__top">{ico}<span>{title}</span></div>
      <div class="ct-card__value">{shown}</div>
      <div>{status_chip(status, indicator=indicator)}</div>
      <div class="ct-card__when">{subtitle}</div>
    </div>"""


def status_legend() -> str:
    """Every label with the one line that explains it."""
    rows = [(GREEN, STATUS_LABELS[GREEN], STATUS_HINTS[GREEN]),
            (YELLOW, STATUS_LABELS[YELLOW], STATUS_HINTS[YELLOW]),
            (RED, NEEDS_CARE, STATUS_HINTS[NEEDS_CARE]),
            (RED, STATUS_LABELS[RED], STATUS_HINTS[RED]),
            (UNKNOWN, STATUS_LABELS[UNKNOWN], STATUS_HINTS[UNKNOWN])]
    items = "".join(f"<div class='ct-legend__item'>{status_chip(s, text=label)}<span>{hint}</span></div>"
                    for s, label, hint in rows)
    return f"<div class='ct-legend'>{items}</div>"


def _layout(fig: go.Figure, height: int = 300, **kw) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        showlegend=False,
        **kw,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(127,127,127,0.2)")
    return fig


def indicator_chart(df: pd.DataFrame, indicator: str, environment: str, height: int = 300) -> go.Figure:
    """Daily values with green / yellow bands drawn behind the line."""
    ind = INDICATORS[indicator]
    table = daily_table(df)
    series = table[indicator].dropna() if indicator in table else pd.Series(dtype=float)
    fig = go.Figure()

    th = get_thresholds(indicator, environment)
    finite = [x for bands in th.values() for b in bands for x in b if abs(x) != float("inf")]
    vals = finite + (series.tolist() if not series.empty else [ind.default])
    span = (max(vals) - min(vals)) or 1.0
    y_min = max(ind.min_valid, min(vals) - 0.1 * span)
    y_max = min(ind.max_valid, max(vals) + 0.1 * span)

    fig.add_hrect(y0=y_min, y1=y_max, fillcolor=BAND_FILL[RED], line_width=0, layer="below")
    for status in (YELLOW, GREEN):
        for lo, hi in th[status]:
            fig.add_hrect(
                y0=max(lo, y_min), y1=min(hi, y_max), fillcolor=BAND_FILL[status], line_width=0, layer="below"
            )

    if not series.empty:
        colors = [STATUS_COLORS[classify(indicator, v, environment)] for v in series.values]
        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=series.values,
                mode="lines+markers",
                line=dict(color=ACCENT, width=2),
                marker=dict(size=9, color=colors, line=dict(width=1, color="#0B0F2A")),
                name=ind.name,
                hovertemplate=f"%{{y:.{ind.decimals}f}} {ind.unit}<extra></extra>",
            )
        )
        if len(series) >= 7:
            roll = series.rolling(7, min_periods=3).mean()
            fig.add_trace(
                go.Scatter(
                    x=roll.index,
                    y=roll.values,
                    mode="lines",
                    line=dict(color="rgba(127,127,127,0.8)", width=1.5, dash="dot"),
                    name="7-day average",
                    hovertemplate=f"7-day avg %{{y:.{ind.decimals}f}}<extra></extra>",
                )
            )
    fig.update_yaxes(range=[y_min, y_max], title=ind.unit)
    return _layout(fig, height, title=dict(text=ind.name, font=dict(size=15)))


def status_heatmap(status_table: pd.DataFrame, height: int = 380) -> go.Figure:
    """Mission calendar: days × indicators, coloured by status."""
    code = {UNKNOWN: 0, GREEN: 1, YELLOW: 2, RED: 3}
    names = [INDICATORS[c].name for c in status_table.columns]
    z = status_table.apply(lambda c: c.map(code)).T.values
    text = status_table.apply(lambda c: c.map(lambda s: status_label(s, c.name))).T.values
    x = [d.strftime("%b %d") for d in pd.to_datetime(status_table.index)]
    colorscale = [
        [0.0, STATUS_COLORS[UNKNOWN]], [0.25, STATUS_COLORS[UNKNOWN]],
        [0.25, STATUS_COLORS[GREEN]], [0.5, STATUS_COLORS[GREEN]],
        [0.5, STATUS_COLORS[YELLOW]], [0.75, STATUS_COLORS[YELLOW]],
        [0.75, STATUS_COLORS[RED]], [1.0, STATUS_COLORS[RED]],
    ]
    fig = go.Figure(
        go.Heatmap(
            z=z, x=x, y=names, text=text, zmin=0, zmax=3, colorscale=colorscale, showscale=False,
            xgap=2, ygap=2, hovertemplate="%{y}<br>%{x}: %{text}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig = _layout(fig, height)
    fig.update_layout(hovermode="closest")
    return fig


def dose_chart(df: pd.DataFrame, height: int = 260) -> go.Figure:
    table = daily_table(df)
    s = table["radiation_dose"].dropna() if "radiation_dose" in table else pd.Series(dtype=float)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s.index, y=s.values, marker_color="#8EA2FF", name="Daily dose",
                         hovertemplate="%{y:.2f} mSv<extra>daily</extra>"))
    fig.add_trace(go.Scatter(x=s.index, y=s.cumsum().values, yaxis="y2", mode="lines",
                             line=dict(color=ACCENT, width=2), name="Cumulative",
                             hovertemplate="%{y:.1f} mSv<extra>cumulative</extra>"))
    fig.update_layout(yaxis=dict(title="mSv / day"),
                      yaxis2=dict(title="cumulative mSv", overlaying="y", side="right", showgrid=False))
    return _layout(fig, height, title=dict(text="Radiation dose", font=dict(size=15)))


def overall_gauge(score: float, height: int = 210) -> go.Figure:
    """Share of indicators in the green zone (0–100)."""
    status = GREEN if score >= 85 else YELLOW if score >= 60 else RED
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=round(score),
            number=dict(suffix="%"),
            title=dict(text="In the normal range", font=dict(size=13)),
            gauge=dict(
                axis=dict(range=[0, 100]),
                bar=dict(color=STATUS_COLORS[status]),
                steps=[dict(range=[0, 60], color=BAND_FILL[RED]), dict(range=[60, 85], color=BAND_FILL[YELLOW]),
                       dict(range=[85, 100], color=BAND_FILL[GREEN])],
            ),
        )
    )
    fig = _layout(fig, height)
    fig.update_layout(margin=dict(l=25, r=25, t=40, b=10))
    return fig
