"""Opening sequence: Earth fades in from darkness, the word "Caretta" appears, then the home screen.

Pure HTML/CSS (no JavaScript, which Streamlit doesn't run in markdown):
* 3 s in total, every step 0.6 s or less: Earth 0.2–0.8 s, word 1.1–1.7 s, fade-out 2.4–3.0 s;
* click anywhere to skip (a hidden checkbox + label, so it works without scripts);
* shown once per session (the caller keeps a flag in session state);
* skipped entirely when the system asks for reduced motion.
The Earth is drawn from ~1,300 dots (an original illustration, not a photograph or an agency image).
"""
from __future__ import annotations

import math
import random

# Coarse continent outlines (longitude, latitude) — just enough to read as Earth from orbit.
_LAND = [
    [(-168, 65), (-140, 70), (-95, 72), (-80, 62), (-65, 60), (-55, 50), (-70, 43), (-80, 30), (-82, 25), (-97, 26),
     (-105, 20), (-95, 16), (-85, 10), (-78, 8), (-90, 15), (-105, 22), (-112, 30), (-118, 34), (-125, 42),
     (-125, 50), (-135, 58), (-150, 60), (-165, 60)],                                             # North America
    [(-55, 60), (-45, 60), (-20, 70), (-20, 80), (-60, 82), (-70, 76)],                          # Greenland
    [(-78, 8), (-60, 10), (-50, 0), (-35, -7), (-40, -22), (-50, -30), (-58, -40), (-68, -55), (-75, -50),
     (-72, -30), (-70, -18), (-80, -5)],                                                          # South America
    [(-10, 36), (-10, 44), (-5, 48), (5, 52), (10, 58), (5, 62), (15, 70), (30, 71), (60, 70), (80, 73),
     (110, 76), (140, 72), (170, 68), (180, 66), (180, 62), (160, 58), (140, 52), (130, 42), (122, 30),
     (120, 22), (108, 18), (105, 10), (98, 15), (92, 22), (80, 8), (75, 20), (66, 25), (57, 25), (50, 30),
     (48, 28), (55, 22), (45, 12), (35, 30), (28, 36), (20, 40), (12, 44), (10, 38), (0, 38)],     # Eurasia
    [(-6, 50), (2, 51), (0, 58), (-6, 58)],                                                       # Great Britain
    [(-17, 21), (-10, 30), (0, 36), (10, 37), (20, 32), (32, 31), (35, 28), (43, 12), (51, 12), (40, -5),
     (40, -15), (35, -25), (20, -35), (17, -28), (12, -15), (10, -2), (8, 4), (-5, 5), (-15, 10)],  # Africa
    [(114, -22), (122, -18), (130, -12), (137, -12), (142, -11), (146, -19), (153, -27), (150, -37),
     (140, -38), (132, -32), (115, -34)],                                                         # Australia
]


def _inside(lon: float, lat: float, poly) -> bool:
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _is_land(lon: float, lat: float) -> bool:
    return lat < -68 or any(_inside(lon, lat, p) for p in _LAND)


def _dot_earth(n: int = 2600, r: float = 150, view_lon: float = -15, view_lat: float = 18) -> str:
    """Earth drawn as dots: a Fibonacci sphere, orthographic view, lit from the upper left."""
    rnd = random.Random(7)
    waves: list[list[str]] = [[], [], []]
    lo0, la0 = math.radians(view_lon), math.radians(view_lat)
    light = (-0.55, -0.45, 0.70)
    norm = math.sqrt(sum(c * c for c in light))
    light = tuple(c / norm for c in light)
    golden = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        y = 1 - 2 * (k + 0.5) / n
        rad = math.sqrt(1 - y * y)
        th = golden * k
        lat = math.asin(y)
        lon = math.atan2(math.sin(th) * rad, math.cos(th) * rad)
        # rotate the globe so (view_lon, view_lat) faces us
        x0 = math.cos(lat) * math.sin(lon - lo0)
        y0 = math.sin(lat)
        z0 = math.cos(lat) * math.cos(lon - lo0)
        yv = y0 * math.cos(la0) - z0 * math.sin(la0)
        zv = y0 * math.sin(la0) + z0 * math.cos(la0)
        if zv <= 0.02:
            continue
        sx, sy = 200 + r * x0, 200 - r * yv
        land = _is_land(math.degrees(lon), math.degrees(lat))
        shade = x0 * light[0] + (-yv) * light[1] + zv * light[2]
        day = max(0.0, min(1.0, 0.55 + 0.9 * shade))
        size = (2.2 if land else 1.6) * (0.45 + 0.55 * zv)
        if land:
            if day < 0.25 and rnd.random() < 0.35:                       # city lights on the night side
                color, op = "#ffd48a", 0.95
            else:
                color, op = "#5fd6a8", 0.25 + 0.75 * day
        else:
            color, op = "#6b9bff", 0.28 + 0.72 * day
        group = rnd.randrange(3)                                         # three fade-in waves
        waves[group].append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{size:.2f}" fill="{color}" '
                            f'fill-opacity="{op:.2f}"/>')
    # a faint ring of atmosphere dots on the limb
    for k in range(120):
        a = 2 * math.pi * k / 120
        waves[2].append(f'<circle cx="{200 + (r + 7) * math.cos(a):.1f}" cy="{200 + (r + 7) * math.sin(a):.1f}" '
                        f'r="1.1" fill="#8fb6ff" fill-opacity="{0.15 + 0.35 * max(0, -math.cos(a + 0.8)):.2f}"/>')
    # Animating three groups instead of ~1,400 separate circles keeps the intro smooth (GPU-composited opacity).
    return "".join(f'<g class="ct-w{k + 1}">{"".join(w)}</g>' for k, w in enumerate(waves))


EARTH_SVG = f"""
<svg class="ct-intro__earth" viewBox="0 0 400 400" aria-hidden="true">
  <defs><radialGradient id="ctE_glow" cx="50%" cy="50%" r="50%">
    <stop offset=".7" stop-color="#5b7cff" stop-opacity=".10"/><stop offset="1" stop-color="#5b7cff" stop-opacity="0"/>
  </radialGradient></defs>
  <circle cx="200" cy="200" r="198" fill="url(#ctE_glow)"/>
  {_dot_earth()}
</svg>
"""

INTRO_CSS = """
<style>
.ct-skip { position: fixed; opacity: 0; pointer-events: none; width: 1px; height: 1px; }
.ct-intro { position: fixed; inset: 0; z-index: 1000000; display: grid; place-items: center; cursor: pointer;
  background: radial-gradient(70% 60% at 50% 45%, #141a48 0%, #0b0f2a 55%, #070a24 100%);
  animation: ct-intro-out .6s ease-in 2.4s forwards; will-change: opacity; }
.ct-skip:checked + .ct-intro { display: none; }
.ct-intro__stage { display: flex; flex-direction: column; align-items: center; gap: 1.4rem; }
.ct-intro__earth { width: min(48vh, 360px); height: auto; }
.ct-intro__earth g { opacity: 0; will-change: opacity; animation: ct-dot .5s ease-out forwards; }
.ct-intro__earth .ct-w1 { animation-delay: .2s; } .ct-intro__earth .ct-w2 { animation-delay: .4s; }
.ct-intro__earth .ct-w3 { animation-delay: .6s; }
@keyframes ct-dot { to { opacity: 1; } }
.ct-intro__word { font-family: 'Fraunces', Georgia, serif; font-weight: 600; font-size: clamp(2.4rem, 6vw, 4.2rem);
  color: #f4f1ff; letter-spacing: .12em; opacity: 0; transform: translateY(8px);
  animation: ct-intro-word .6s cubic-bezier(.2,.7,.2,1) 1.1s forwards; }
.ct-intro__word span { color: #f5b041; }
.ct-intro__hint { position: absolute; bottom: 2rem; font-size: .8rem; color: #a3a9d6; opacity: 0;
  animation: ct-intro-word .4s ease 1.4s forwards; }
@keyframes ct-intro-word { to { opacity: 1; transform: none; letter-spacing: .04em; } }
@keyframes ct-intro-out { to { opacity: 0; visibility: hidden; pointer-events: none; } }
@media (prefers-reduced-motion: reduce) { .ct-intro, .ct-skip { display: none !important; } }
</style>
"""


def intro_html() -> str:
    return (
        INTRO_CSS
        + '<input type="checkbox" id="ct-skip" class="ct-skip" aria-label="Skip intro">'
        + '<label for="ct-skip" class="ct-intro" title="Click to skip"><div class="ct-intro__stage">'
        + EARTH_SVG
        + '<div class="ct-intro__word">Caretta<span>.</span></div></div>'
        + '<div class="ct-intro__hint">Click anywhere to skip</div></label>'
    )


def render_intro_once() -> None:
    """Show the opening sequence the first time the home screen is opened in this session."""
    import streamlit as st

    # Always take the same slot in the page, shown or not: Streamlit identifies elements by position, and
    # a missing element would shift the body-map component and make its iframe reload on every rerun.
    slot = st.empty()
    if st.session_state.get("_intro_shown"):
        return
    st.session_state["_intro_shown"] = True
    # st.markdown keeps inline SVG (st.html's sanitizer drops it); collapse whitespace so markdown
    # doesn't read indented lines as a code block
    slot.markdown(" ".join(line.strip() for line in intro_html().splitlines()), unsafe_allow_html=True)
