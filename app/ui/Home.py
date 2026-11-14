"""Caretta entry point and page router.

Run:  streamlit run app/ui/Home.py   (or double-click start.bat)

The home screen is the living body map (views/home.py). The old stand-alone
Body Map page is folded into it, so it is not listed here any more.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.ui import STATIC  # noqa: E402

st.set_page_config(page_title="Caretta", page_icon=str(STATIC / "favicon.png"), layout="wide")

pages = [
    st.Page("views/home.py", title="Home", default=True),
    st.Page("pages/1_Check_In.py", title="Check in", url_path="check-in"),
    st.Page("pages/1_Diagnosis.py", title="How are you feeling?", url_path="diagnosis"),
    st.Page("pages/3_Trends.py", title="Trends", url_path="trends"),
    st.Page("views/progress.py", title="Your progress", url_path="progress"),
    st.Page("pages/4_Flight_Surgeon.py", title="Care team", url_path="care-team"),
    st.Page("pages/4_Gallery.py", title="Gallery", url_path="gallery"),
    st.Page("pages/5_About.py", title="About", url_path="about"),
]
st.navigation(pages).run()
