"""Illustrated mission patches (inline SVG, original artwork).

Each patch looks like an embroidered crew patch: a twill background, a satin
border with stitch marks, a small scene and the title sewn around the top.
Locked patches are shown as a faint outline so there is something to look
forward to, never something that was lost.
"""
from __future__ import annotations

from html import escape

# palette: deep navy twill, gold thread, NASAWDS-style blues and a warm red
NAVY, NAVY2, GOLD, CREAM = "#14233f", "#0c1628", "#f2c14e", "#f4ead2"
BLUE, CYAN, RED, GREEN, VIOLET = "#2672de", "#00bde3", "#e52207", "#3cb371", "#8a6cf0"

_SCENES = {
    # sunrise over a planet's limb
    "first_light": f"""
      <circle cx="60" cy="96" r="44" fill="{BLUE}"/>
      <path d="M16 96 A44 44 0 0 1 104 96" fill="none" stroke="{CYAN}" stroke-width="3"/>
      <circle cx="60" cy="58" r="11" fill="{GOLD}"/>
      <g stroke="{GOLD}" stroke-width="2.4" stroke-linecap="round">
        <line x1="60" y1="40" x2="60" y2="34"/><line x1="44" y1="47" x2="40" y2="43"/>
        <line x1="76" y1="47" x2="80" y2="43"/><line x1="38" y1="60" x2="32" y2="60"/>
        <line x1="82" y1="60" x2="88" y2="60"/></g>""",
    # seven stars arcing over a crescent
    "first_week": f"""
      <path d="M48 52 a20 20 0 1 0 22 30 a16 16 0 1 1 -22 -30z" fill="{CREAM}"/>
      {"".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{GOLD}"/>' for x, y in
               [(30, 62), (34, 48), (43, 38), (56, 33), (70, 34), (82, 41), (90, 53)])}""",
    # a loggerhead turtle swimming through stars (Caretta caretta)
    "steady_hand": f"""
      <g transform="translate(60 64) rotate(-20)">
        <ellipse cx="0" cy="0" rx="22" ry="17" fill="#8a5a2b"/>
        <path d="M-11 -9 L0 -14 L11 -9 L11 7 L0 12 L-11 7z" fill="#b37a3c" stroke="#5d3a1a" stroke-width="1.4"/>
        <path d="M0 -14 V12 M-11 -1 H11" stroke="#5d3a1a" stroke-width="1.2"/>
        <ellipse cx="27" cy="-1" rx="7" ry="6" fill="#9c6b37"/>
        <circle cx="30" cy="-3" r="1.3" fill="{NAVY2}"/>
        <path d="M-12 -14 q-14 -14 -22 -6 q10 2 16 12z M12 -14 q8 -18 20 -12 q-10 4 -12 14z" fill="#9c6b37"/>
        <path d="M-14 13 q-10 8 -16 4 q6 -6 12 -10z M14 13 q8 8 14 6 q-4 -6 -10 -10z" fill="#9c6b37"/>
      </g>
      {"".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{CREAM}"/>' for x, y in [(30, 40), (88, 44), (36, 88), (86, 86)])}""",
    # crescent moon over a sleeping capsule window
    "deep_rest": f"""
      <path d="M68 34 a24 24 0 1 0 14 40 a19 19 0 1 1 -14 -40z" fill="{CREAM}"/>
      <rect x="30" y="72" width="34" height="22" rx="11" fill="{NAVY2}" stroke="{CYAN}" stroke-width="2.4"/>
      <path d="M38 83 h18" stroke="{VIOLET}" stroke-width="3" stroke-linecap="round"/>
      {"".join(f'<circle cx="{x}" cy="{y}" r="1.8" fill="{GOLD}"/>' for x, y in [(36, 44), (46, 58), (90, 88)])}""",
    # a figure running on a treadmill harness, with an orbit swoosh
    "strong_frame": f"""
      <ellipse cx="60" cy="66" rx="36" ry="12" fill="none" stroke="{CYAN}" stroke-width="2.6"
               transform="rotate(-18 60 66)"/>
      <g stroke="{CREAM}" stroke-width="4.5" stroke-linecap="round" fill="none">
        <circle cx="62" cy="38" r="6" fill="{CREAM}" stroke="none"/>
        <path d="M60 46 L56 66"/><path d="M58 52 L46 58 M58 52 L70 58 L76 52"/>
        <path d="M56 66 L46 80 L38 80 M56 66 L66 76 L64 88"/></g>
      <line x1="30" y1="92" x2="88" y2="92" stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>""",
    # an antenna dish sending a signal home
    "open_channel": f"""
      <circle cx="88" cy="40" r="10" fill="{BLUE}"/><path d="M80 36 q8 6 16 0" stroke="{GREEN}" stroke-width="3" fill="none"/>
      <path d="M30 86 L44 66" stroke="{CREAM}" stroke-width="4" stroke-linecap="round"/>
      <path d="M26 64 a22 22 0 0 0 34 18 z" fill="{CREAM}"/>
      <g fill="none" stroke="{GOLD}" stroke-width="2.6" stroke-linecap="round">
        <path d="M56 58 q6 -6 12 -2"/><path d="M58 50 q12 -10 22 -4"/><path d="M60 42 q16 -14 30 -6"/></g>""",
}


def patch_svg(patch_id: str, title: str, earned: bool, size: int = 116) -> str:
    """One patch as an inline SVG string."""
    scene = _SCENES.get(patch_id, "")
    uid = f"p_{patch_id}_{'on' if earned else 'off'}"
    label = escape(title.upper())
    style = "" if earned else "filter:grayscale(1) brightness(.75);opacity:.38"
    return f"""<svg viewBox="0 0 120 120" width="{size}" height="{size}" role="img"
  aria-label="{escape(title)} patch{'' if earned else ' (not earned yet)'}" style="{style}">
  <defs>
    <radialGradient id="{uid}_bg" cx="50%" cy="38%" r="70%"><stop offset="0" stop-color="{NAVY}"/><stop offset="1" stop-color="{NAVY2}"/></radialGradient>
    <pattern id="{uid}_tw" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="4" height="4" fill="none"/><line x1="0" y1="0" x2="0" y2="4" stroke="#ffffff" stroke-opacity=".05" stroke-width="1.4"/></pattern>
    <clipPath id="{uid}_c"><circle cx="60" cy="60" r="46"/></clipPath>
    <path id="{uid}_arc" d="M18 62 A42 42 0 0 1 102 62"/>
  </defs>
  <circle cx="60" cy="60" r="58" fill="{GOLD if earned else '#6b7280'}"/>
  <circle cx="60" cy="60" r="58" fill="none" stroke="#000" stroke-opacity=".25" stroke-width="1"/>
  <circle cx="60" cy="60" r="54.5" fill="none" stroke="{NAVY2}" stroke-width="1.2" stroke-dasharray="2.2 2.2"/>
  <circle cx="60" cy="60" r="50" fill="url(#{uid}_bg)"/>
  <circle cx="60" cy="60" r="50" fill="url(#{uid}_tw)"/>
  <g clip-path="url(#{uid}_c)"><g transform="translate(60 67) scale(.84) translate(-60 -60)">{scene}</g></g>
  <circle cx="60" cy="60" r="46" fill="none" stroke="{GOLD if earned else '#9ca3af'}" stroke-width="1.2" stroke-dasharray="1.6 1.8" stroke-opacity=".8"/>
  <text font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-size="8.6" font-weight="700" letter-spacing="1.6" fill="{CREAM}">
    <textPath href="#{uid}_arc" startOffset="50%" text-anchor="middle">{label}</textPath></text>
</svg>"""


def patches_grid_html(items: list[tuple[str, str, bool, str]], size: int = 104) -> str:
    """items: (id, title, earned, caption). Responsive grid of patches with a caption under each."""
    cells = "".join(
        f"""<figure class="ct-patch{' ct-patch--locked' if not earned else ''}" title="{escape(caption)}">
        {patch_svg(pid, title, earned, size)}
        <figcaption><b>{escape(title)}</b><span>{escape(caption)}</span></figcaption></figure>"""
        for pid, title, earned, caption in items
    )
    return f'<div class="ct-patches">{cells}</div>'
