"""Step-by-step triage: answer a few questions, get a likely explanation and what to do next."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.api import db  # noqa: E402
from app.core.diagnosis import OUTCOMES, URGENCY, Outcome, assess, max_depth, walk  # noqa: E402
from app.core.indicators import HAZARDS  # noqa: E402
from app.ui import page_context, setup_page  # noqa: E402
from app.ui.charts import status_chip  # noqa: E402

setup_page("Diagnosis")
ctx = page_context()
ss = st.session_state

# answers are kept per crew member, so switching people doesn't mix up their triage
akey = f"_dx_{ctx.astronaut}_{ctx.environment}"
ss.setdefault(akey, [])
answers: list[int] = ss[akey]


def choose(i: int) -> None:
    ss[akey] = [*ss[akey], i]
    ss.pop("_dx_saved", None)


def back() -> None:
    ss[akey] = ss[akey][:-1]
    ss.pop("_dx_saved", None)


def restart() -> None:
    ss[akey] = []
    ss.pop("_dx_saved", None)


st.title("How are you feeling?")
st.caption("Not feeling right? Answer a few quick questions and you'll get the most likely explanation, "
           "what to do about it, and who to tell. We also look at your latest check-in numbers.")

steps, current = walk(answers)

if isinstance(current, Outcome):
    # ------------------------------------------------------------- result
    result = assess(answers, ctx.statuses, ctx.environment)
    u = URGENCY[result.urgency]
    st.markdown(
        f"""<div style="border-radius:12px;padding:16px 20px;border:2px solid {u['color']};
        background:{u['color']}14;margin:6px 0 14px">
        <div style="font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;color:{u['color']};
        font-weight:700">{u['label']}</div>
        <div style="font-size:1.55rem;font-weight:700;margin:2px 0 4px">{result.title}</div>
        <div style="opacity:.85">{u['who']}</div></div>""",
        unsafe_allow_html=True,
    )
    if result.urgency != result.base_urgency:
        st.warning("We raised the urgency because of your latest readings (see below).")

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.markdown(f"**What's probably going on**  \n{result.explanation}")
        st.markdown("**What to do**")
        st.markdown("\n".join(f"{i}. {a}" for i, a in enumerate(result.actions, 1)))
        for n in result.notes:
            st.info(n)
        hazard = OUTCOMES[result.outcome_id].hazard
        if hazard:
            h = HAZARDS[hazard]
            st.caption(f"Related spaceflight hazard: {h['name'].lower()}. {h['summary']}")
    with right:
        st.markdown("**Your latest numbers**")
        if not result.evidence:
            st.caption("No measurements are needed for this one.")
        for e in result.evidence:
            st.markdown(f"{status_chip(e['status'], indicator=e['indicator'])} &nbsp;{e['name']}: **{e['value']}**",
                        unsafe_allow_html=True)
        with st.expander("Your answers"):
            for a in result.answers:
                st.markdown(f"- {a['question']} → **{a['answer']}**")

    c1, c2, c3 = st.columns(3)
    if ss.get("_dx_saved") == akey:
        c1.success("Saved to your medical log.")
    elif c1.button("Save to medical log", type="primary", width="stretch"):
        db.insert_diagnosis(ctx.conn, ctx.astronaut, result.to_dict(), ctx.environment)
        ss["_dx_saved"] = akey
        st.rerun()
    c2.button("Change last answer", on_click=back, width="stretch")
    c3.button("Start over", on_click=restart, width="stretch")
    st.caption("This is decision support, not a diagnosis. If something feels seriously wrong, "
               "trust that feeling and call your CMO.")
else:
    # ----------------------------------------------------------- question
    depth = max_depth()
    st.progress(min(len(answers) / depth, 0.95), text=f"Question {len(answers) + 1}")
    with st.container(border=True):
        st.markdown(f"### {current.text}")
        if current.hint:
            st.caption(current.hint)
        two_cols = len(current.options) > 5
        cols = st.columns(2) if two_cols else [st.container()]
        for i, opt in enumerate(current.options):
            target = cols[i % 2] if two_cols else cols[0]
            emergency_opt = current.id == "start" and i < len(current.options) - 1
            target.button(
                opt.label,
                key=f"dx_{current.id}_{i}",
                on_click=choose,
                args=(i,),
                width="stretch",
                type="secondary" if not emergency_opt else "tertiary",
            )
    if answers:
        b1, b2, _ = st.columns([1, 1, 3])
        b1.button("Back", on_click=back, width="stretch")
        b2.button("Start over", on_click=restart, width="stretch")
    if steps:
        st.caption("So far: " + " · ".join(o.label for _, o in steps))

# -------------------------------------------------------------- history
st.divider()
st.subheader("Earlier assessments")
hist = db.fetch_diagnoses(ctx.conn, ctx.astronaut, ctx.environment)
if hist.empty:
    st.caption("Nothing saved yet.")
for row in hist.head(10).to_dict("records"):
    u = URGENCY.get(row["urgency"], URGENCY["self"])
    with st.expander(f"{row['ts']:%d %b, %H:%M} — {row['title']}"):
        st.markdown(f"<span style='color:{u['color']};font-weight:700'>{u['label']}</span>", unsafe_allow_html=True)
        d = row["details"]
        st.markdown("\n".join(f"{i}. {a}" for i, a in enumerate(d.get("actions", []), 1)))
        if st.button("Delete", key=f"dxdel_{row['id']}"):
            db.delete_diagnosis(ctx.conn, row["id"])
            st.rerun()
