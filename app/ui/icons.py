"""Caretta's line icons: one consistent set, drawn for this app.

Every icon is a 24×24 inline SVG with a 1.5 px stroke, round caps and joins,
no fills, and ``currentColor`` — so it takes the colour of the text around it.
"""
from __future__ import annotations

_P = {
    # measurements
    "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    "pulse": '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
    "gauge": '<path d="M4.5 16a8 8 0 1 1 15 0"/><path d="M12 15l3.5-5"/><circle cx="12" cy="15.5" r="1"/>',
    "lungs": '<path d="M12 4v7M12 11l-3 2M12 11l3 2"/><path d="M9 7.5C6 8 4 12 4 16.5c0 1.6 1.3 2.5 2.8 2C8.3 18 9 17 9 15.5V7.5z"/>'
             '<path d="M15 7.5c3 .5 5 4.5 5 9 0 1.6-1.3 2.5-2.8 2-1.5-.5-2.2-1.5-2.2-3V7.5z"/>',
    "thermometer": '<path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a3.5 3.5 0 1 1-4 0z"/><path d="M12 9v7"/>',
    "droplet": '<path d="M12 3.5s6 6.4 6 10.5a6 6 0 0 1-12 0c0-4.1 6-10.5 6-10.5z"/><path d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
    "moon": '<path d="M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z"/>',
    "smile": '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 14a4.5 4.5 0 0 0 7 0"/><path d="M9.5 9.5h.01M14.5 9.5h.01"/>',
    "dumbbell": '<path d="M6.5 7v10M17.5 7v10M4 9.5v5M20 9.5v5M6.5 12h11"/>',
    "radiation": '<circle cx="12" cy="12" r="1.4"/><path d="M13.50 14.60L16.25 19.36A8.5 8.5 0 0 1 7.75 19.36L10.50 14.60A3.0 3.0 0 0 0 13.50 14.60z"/><path d="M9.00 12.00L3.50 12.00A8.5 8.5 0 0 1 7.75 4.64L10.50 9.40A3.0 3.0 0 0 0 9.00 12.00z"/><path d="M13.50 9.40L16.25 4.64A8.5 8.5 0 0 1 20.50 12.00L15.00 12.00A3.0 3.0 0 0 0 13.50 9.40z"/>',
    # body systems
    "brain": '<path d="M9 4.5a3 3 0 0 0-3 3 3 3 0 0 0-1.5 5.3A3 3 0 0 0 8 17.5a2.5 2.5 0 0 0 4 1V5.6A2.5 2.5 0 0 0 9 4.5z"/>'
             '<path d="M15 4.5a3 3 0 0 1 3 3 3 3 0 0 1 1.5 5.3 3 3 0 0 1-3.5 4.7 2.5 2.5 0 0 1-4 1"/>',
    "bone": '<path d="M8.5 15.5l7-7"/><path d="M8.5 15.5a2.2 2.2 0 1 1-3 1.5 2.2 2.2 0 1 1 1.5-3"/>'
            '<path d="M15.5 8.5a2.2 2.2 0 1 1 3-1.5 2.2 2.2 0 1 1-1.5 3"/>',
    "shield": '<path d="M12 3.5l7 2.5v5.5c0 4.5-3 7.6-7 9-4-1.4-7-4.5-7-9V6z"/><path d="M9.5 12l2 2 3.5-4"/>',
    "flask": '<path d="M10 3.5h4M10.5 3.5v5.2L5.6 17a2.4 2.4 0 0 0 2 3.5h8.8a2.4 2.4 0 0 0 2-3.5l-4.9-8.3V3.5"/><path d="M8 14h8"/>',
    "body": '<circle cx="12" cy="5" r="2"/><path d="M8 21l1-7-3-1 2-5h8l2 5-3 1 1 7"/>',
    # hazards & places
    "planet": '<circle cx="12" cy="12" r="5.5"/><path d="M4.5 14.5c-2 1.8-2.4 3.3-1.4 3.9 1.7 1 7.4-1.2 12.6-4.6 5.2-3.4 8.2-6.9 6.6-7.9-.9-.6-2.6-.2-4.8.9"/>',
    "signal": '<circle cx="12" cy="17" r="1.3"/><path d="M8.5 13.5a5 5 0 0 1 7 0M5.5 10.5a9 9 0 0 1 13 0M2.8 7.5a13 13 0 0 1 18.4 0"/>',
    "satellite": '<rect x="9.5" y="9.5" width="5" height="5" rx="1"/><rect x="2.5" y="9" width="4.5" height="6" rx=".6"/><rect x="17" y="9" width="4.5" height="6" rx=".6"/><path d="M7 12h2.5M14.5 12H17M12 9.5V6.8M10.2 5.2a2.5 2.5 0 0 1 3.6 0M4.75 9v6M19.25 9v6"/>',
    "isolation": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="10" r="2.4"/><path d="M7.8 17.3a5 5 0 0 1 8.4 0"/>',
    "earth": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.6 2.4 3.8 5.3 3.8 8.5S14.6 18.1 12 20.5M12 3.5C9.4 5.9 8.2 8.8 8.2 12s1.2 6.1 3.8 8.5"/>',
    # app
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "circle": '<circle cx="12" cy="12" r="7.5"/>',
    "dot": '<circle cx="12" cy="12" r="3"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "calendar": '<rect x="4" y="5.5" width="16" height="14.5" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "camera": '<path d="M4 8.5h3l1.6-2.5h6.8L17 8.5h3v10H4z"/><circle cx="12" cy="13.2" r="3.3"/>',
    "image": '<rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M20.5 16l-5-5-8 8"/>',
    "stethoscope": '<path d="M6 3.5v5a4 4 0 0 0 8 0v-5"/><path d="M10 12.5v2a4.5 4.5 0 0 0 9 0V13"/><circle cx="19" cy="11" r="2"/>',
    "chat": '<path d="M4.5 5.5h15v10h-8l-4.5 3.5v-3.5H4.5z"/>',
    "alert": '<path d="M12 4l9 15.5H3z"/><path d="M12 10v4M12 17h.01"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5M12 8h.01"/>',
    "arrow": '<path d="M5 12h14M13.5 6.5L19 12l-5.5 5.5"/>',
    "sparkle": '<path d="M12 3.5l1.8 5.2 5.2 1.8-5.2 1.8L12 17.5l-1.8-5.2L5 10.5l5.2-1.8z"/>',
    "patch": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="5.5" stroke-dasharray="1.6 1.6"/><path d="M12 9.2l.9 1.9 2 .3-1.5 1.4.4 2-1.8-1-1.8 1 .4-2-1.5-1.4 2-.3z"/>',
}

#: one icon per health indicator, body region and spaceflight hazard
INDICATOR_ICONS = {
    "heart_rate": "pulse", "systolic_bp": "gauge", "diastolic_bp": "gauge", "spo2": "lungs",
    "body_temp": "thermometer", "blood_glucose": "droplet", "sleep_hours": "moon", "mood": "smile",
    "exercise_minutes": "dumbbell", "radiation_dose": "radiation",
}
REGION_ICONS = {
    "brain": "brain", "heart": "heart", "lungs": "lungs", "metabolism": "flask", "immune": "shield",
    "musculoskeletal": "bone", "whole_body": "radiation",
}
HAZARD_ICONS = {
    "radiation": "radiation", "isolation": "isolation", "distance": "signal", "gravity": "planet",
    "environment": "satellite",
}


def icon(name: str, size: int = 18, cls: str = "ct-ico", title: str | None = None) -> str:
    """Inline SVG for ``name``. Decorative unless a ``title`` is given."""
    body = _P.get(name, _P["circle"])
    label = f'role="img" aria-label="{title}"' if title else 'aria-hidden="true"'
    return (f'<svg class="{cls}" {label} width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def names() -> list[str]:
    return list(_P)
