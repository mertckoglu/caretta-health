"""Guided check-in: type the values you measured, see the status instantly, attach photos, earn XP."""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.api import db  # noqa: E402
from app.core.indicators import HAZARDS, INDICATORS  # noqa: E402
from app.core.recommend import recommend, task_progress  # noqa: E402
from app.core.thresholds import ENVIRONMENTS, GREEN, RED, classify, green_range  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import status_chip  # noqa: E402

setup_page("Check-in")
ctx = page_context()
ss = st.session_state

st.title("Check-in")
st.caption(f"Logging for **{ctx.astronaut}** in **{ENVIRONMENTS[ctx.environment]['label']}**. "
           "Fill in what you measured and leave the rest blank. You'll see right away whether a number is in range.")

# Result of the previous save (shown once after rerun)
if res := ss.pop("_last_checkin", None):
    parts = []
    if res["n"]:
        parts.append(f"{res['n']} reading(s)")
    if res["photos"]:
        parts.append(f"{res['photos']} photo(s) → Gallery")
    st.success("Thanks, that's saved: " + " and ".join(parts) + f". You've done {res['done']} of today's "
               f"{res['planned']} routine items.")
    if res["red"]:
        st.toast("One of these needs attention. The steps are below, and you're not on your own with it.")
    for r in res["recs"]:
        if r["status"] != GREEN:
            with st.container(border=True):
                st.markdown(f"{status_chip(r['status'], indicator=r['indicator'])} **{r['title']}**",
                            unsafe_allow_html=True)
                for a in r["actions"]:
                    st.markdown(f"- {a}")
for err in ss.pop("_checkin_errors", []):
    st.error(err)

due = {i for t in task_progress(ctx.df) if t["state"] == "due" for i in t["indicators"]}

MOOD_LABELS = {1: "1", 2: "2", 3: "3", 4: "4", 5: "5"}
MOOD_HELP = "1 very low · 2 low · 3 okay · 4 good · 5 great"
GROUPS = {
    "Morning, before breakfast": ["heart_rate", "systolic_bp", "diastolic_bp", "spo2", "body_temp",
                                       "blood_glucose", "sleep_hours"],
    "Later in the day": ["exercise_minutes", "mood", "radiation_dose"],
}
ss.setdefault("_form_nonce", 0)
nonce = ss["_form_nonce"]          # bumping it gives fresh, empty widgets after a save


def wkey(name: str) -> str:
    return f"ci_{name}_{nonce}"


entries: dict[str, float] = {}
for group, keys in GROUPS.items():
    st.subheader(group)
    for key in keys:
        ind = INDICATORS[key]
        c_name, c_val, c_status, c_help = st.columns([1.5, 1.8, 2.1, 0.85], vertical_alignment="center")
        c_name.markdown(f"**{ind.name}**" + (" <span style='color:#B7791F;font-size:.8rem'>due</span>"
                                             if key in due else ""), unsafe_allow_html=True)
        if key == "mood":
            value = c_val.segmented_control("Mood", list(MOOD_LABELS), format_func=MOOD_LABELS.get,
                                            key=wkey(key), help=MOOD_HELP, label_visibility="collapsed")
            c_val.caption("1 very low · 3 okay · 5 great")
        else:
            value = c_val.number_input(
                f"{ind.name} ({ind.unit})",
                min_value=float(ind.min_valid),
                max_value=float(ind.max_valid),
                value=None,
                step=float(ind.step),
                format=f"%.{ind.decimals}f",
                placeholder=f"e.g. {ind.default:g} {ind.unit}",
                key=wkey(key),
                label_visibility="collapsed",
            )
        lo, hi = green_range(key, ctx.environment)
        target = f"{lo:g}–{hi:g}" if hi != float("inf") else f"≥ {lo:g}"
        if value is not None:
            entries[key] = float(value)
            c_status.markdown(f"{status_chip(classify(key, float(value), ctx.environment), indicator=key)} "
                              f"<span style='opacity:.65;font-size:.8rem'>target {target} {ind.unit}</span>",
                              unsafe_allow_html=True)
        else:
            c_status.markdown(f"<span style='opacity:.5;font-size:.8rem'>target {target} {ind.unit}</span>",
                              unsafe_allow_html=True)
        with c_help.popover("How?", help=f"How to measure {ind.name.lower()}"):
            st.markdown(f"**How:** {ind.how_to_measure}")
            st.markdown(f"**Why it matters:** {ind.why_it_matters}")
            st.markdown("**Linked to:** " + ", ".join(HAZARDS[h]["name"].lower() for h in ind.hazards) + ".")

st.subheader("Photos")
st.caption("Optional. Useful for a rash, a cut, swelling or a red eye. Photos go to the Gallery, and "
           "the flight surgeon can see them too.")
pc1, pc2 = st.columns(2)
category = pc1.selectbox("What does it show?", list(db.PHOTO_CATEGORIES), format_func=db.PHOTO_CATEGORIES.get,
                         key=wkey("photo_cat"))
caption = pc2.text_input("Caption", placeholder="e.g. red patch on left forearm, itchy", key=wkey("photo_caption"))
tab_cam, tab_up = st.tabs(["Camera", "Upload"])
with tab_cam:
    shot = st.camera_input("Take a photo", key=wkey("camera")) if st.toggle("Use the camera", key=wkey("cam_on")) else None
with tab_up:
    uploads = st.file_uploader("Upload photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                               key=wkey("upload")) or []
photos = ([shot] if shot is not None else []) + list(uploads)
if photos:
    thumbs = st.columns(min(len(photos), 6))
    for i, ph in enumerate(photos[:6]):
        thumbs[i].image(ph, width="stretch")

note = st.text_area("Anything else? (optional)", placeholder="How are you feeling? e.g. headache since lunch",
                    key=wkey("note"))

c1, c2 = st.columns(2)
day = c1.date_input("Date", value=datetime.now().date(), key=wkey("date"))
tm = c2.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0), key=wkey("time"))


def _save(entries: dict[str, float], photos: list, ts: datetime, note: str, category: str, caption: str) -> None:
    """Runs as a button callback, i.e. before the next script run — so the form can be reset cleanly."""
    errors = []
    note_text = note.strip() or None
    for key, value in entries.items():
        db.insert_reading(ctx.conn, ctx.astronaut, key, value, ts, ctx.environment, note_text)
    saved_photos = 0
    for ph in photos:
        try:
            db.insert_photo(ctx.conn, ctx.astronaut, ph.getvalue(), ph.type or "image/jpeg", ts, ctx.environment,
                            category, caption or note_text)
            saved_photos += 1
        except ValueError as exc:
            errors.append(f"Photo {getattr(ph, 'name', '')} not saved: {exc}")
    today_tasks = task_progress(db.fetch_readings(ctx.conn, ctx.astronaut, environment=ctx.environment), ts.date())
    statuses = {k: classify(k, v, ctx.environment) for k, v in entries.items()}
    ss["_last_checkin"] = {
        "n": len(entries),
        "photos": saved_photos,
        "done": sum(t["state"] == "done" for t in today_tasks),
        "planned": len(today_tasks),
        "red": any(s == RED for s in statuses.values()),
        "recs": [recommend(k, v, statuses[k], ctx.environment).to_dict() for k, v in entries.items()],
    }
    ss["_checkin_errors"] = errors
    ss["_form_nonce"] += 1        # fresh empty form


label = []
if entries:
    label.append(f"{len(entries)} reading(s)")
if photos:
    label.append(f"{len(photos)} photo(s)")
st.button(
    "Save check-in",
    type="primary",
    disabled=not label,
    width="stretch",
    on_click=_save,
    args=(entries, photos, datetime.combine(day, tm), note, category, caption),
)
if not label:
    st.caption("Enter at least one number or add a photo, then save.")
