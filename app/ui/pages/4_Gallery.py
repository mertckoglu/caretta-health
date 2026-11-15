"""Photo gallery: every photo taken or uploaded during check-in, filterable and shareable with the flight surgeon."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from app.api import db  # noqa: E402
from app.core.thresholds import ENVIRONMENTS  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402

setup_page("Gallery")
ctx = page_context()
ss = st.session_state

st.title("Gallery")
st.caption("Photos you took during check-ins. Looking at them side by side is the easiest way to tell whether "
           "something is healing.")

ICONS = {k: "" for k in ("skin", "eye", "wound", "swelling", "mouth", "other")}

f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.6, 1])
who = f1.selectbox("Crew", ["me", "all"], format_func=lambda k: ctx.astronaut if k == "me" else "Whole crew")
where = f2.selectbox("Environment", ["here", "all"],
                     format_func=lambda k: ENVIRONMENTS[ctx.environment]["label"] if k == "here" else "All environments")
cat = f3.selectbox("Category", ["all", *db.PHOTO_CATEGORIES],
                   format_func=lambda k: "All categories" if k == "all" else db.PHOTO_CATEGORIES[k])
per_row = f4.selectbox("Per row", [2, 3, 4, 5], index=2)

photos = db.fetch_photos(
    ctx.conn,
    astronaut_id=ctx.astronaut if who == "me" else None,
    environment=ctx.environment if where == "here" else None,
    category=None if cat == "all" else cat,
)

if photos.empty:
    st.info("No photos yet. You can add one at the bottom of the check-in page.")
    try:
        st.page_link("pages/1_Check_In.py", label="Go to check-in")
    except Exception:  # page registry unavailable (e.g. page run on its own in tests)
        pass
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Photos", len(photos))
m2.metric("Days with photos", photos["ts"].dt.date.nunique())
m3.metric("Latest", photos["ts"].max().strftime("%d %b %H:%M"))


@st.dialog("Photo", width="large")
def show_photo(row: dict) -> None:
    path = db.photo_path(ctx.conn, row["filename"])
    if not path.exists():
        st.error("The image file is missing from the photos folder.")
        return
    with Image.open(path) as im:                       # fit inside the dialog, keep aspect ratio
        im = ImageOps.exif_transpose(im)
        im.thumbnail((1100, 560))
        preview = im.convert("RGB") if im.mode not in ("RGB", "L") else im.copy()
    st.image(preview, width="content")
    st.markdown(f"**{ICONS.get(row['category'], '')} {db.PHOTO_CATEGORIES.get(row['category'], row['category'])}** · "
                f"{row['astronaut_id']} · {row['ts']:%d %b %Y %H:%M} · {ENVIRONMENTS.get(row['environment'], {}).get('label', row['environment'])}")
    new_caption = st.text_input("Caption", value=row["caption"] or "", key=f"cap_{row['id']}")
    new_cat = st.selectbox("Category", list(db.PHOTO_CATEGORIES), index=list(db.PHOTO_CATEGORIES).index(row["category"]),
                           format_func=db.PHOTO_CATEGORIES.get, key=f"cat_{row['id']}")
    c1, c2, c3 = st.columns(3)
    if c1.button("Save", key=f"save_{row['id']}", width="stretch"):
        db.update_photo(ctx.conn, row["id"], caption=new_caption, category=new_cat)
        st.rerun()
    c2.download_button("Download", path.read_bytes(), file_name=row["filename"], mime=row["mime"],
                       key=f"dl_{row['id']}", width="stretch")
    confirm = c3.checkbox("Yes, delete it", key=f"conf_{row['id']}")
    if c3.button("Delete photo", key=f"del_{row['id']}", disabled=not confirm, width="stretch"):
        db.delete_photo(ctx.conn, row["id"])
        st.rerun()


for day, group in photos.groupby(photos["ts"].dt.date, sort=False):
    st.subheader(f"{day:%A, %d %B %Y}")
    rows = group.to_dict("records")
    for start in range(0, len(rows), per_row):
        cols = st.columns(per_row)
        for col, row in zip(cols, rows[start : start + per_row]):
            with col.container(border=True):
                thumb = db.thumb_path(ctx.conn, row["filename"])
                if thumb.exists():
                    st.image(str(thumb), width="stretch")
                else:
                    st.warning("Image file not found")
                st.markdown(f"{ICONS.get(row['category'], '')} **{db.PHOTO_CATEGORIES.get(row['category'], row['category'])}**")
                st.caption(f"{row['ts']:%H:%M} · {row['astronaut_id']}" + (f"  \n{row['caption']}" if row["caption"] else ""))
                if st.button("View", key=f"open_{row['id']}", width="stretch"):
                    show_photo(row)
