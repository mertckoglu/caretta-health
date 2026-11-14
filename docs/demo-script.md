# Demo script (≈ 4 minutes)

**Setup** (before the demo)

```bash
pip install -r requirements.txt
python scripts/seed_demo_data.py --db --reset      # 4-person crew, 30 days ending today
streamlit run app/ui/Home.py                       # http://localhost:8501
uvicorn app.api.main:app --port 8000               # optional, http://localhost:8000/docs
```

The demo mission (commander **CDR**, ISS) contains scripted events:
day 12 solar particle event, days 16–18 treadmill out of service, days 22–23 fever,
a mid-mission mood dip ("third-quarter phenomenon") and gradual sleep erosion.

---

### 1. The problem (30 s)
"Mars crews will be 4–24 light-minutes away from their doctors. NASA's five hazards — radiation,
isolation, distance, gravity, hostile environment — affect every body system. Astronauts need to
assess themselves, understand the result and know when to call for help."

### 2. Home dashboard (45 s)
* Banner shows the **overall status** at a glance (colour + icon + words).
* Ten indicator cards; the yellow **Sleep** card stands out.
* "What to do now" gives concrete actions and **who** should act.
* Right column: % of indicators in green, **today's routine** with due tasks, XP, level, streak, badges.

### 3. Check-in (60 s)
* Open **Check In**. Due measurements are pre-ticked.
* Enter heart rate **118** → chip turns 🟡 instantly, with the target range.
* Open "How to measure · Fasting blood glucose" → microgravity tip about capturing the drop.
* Enter SpO₂ **90** → 🔴. Save → XP toast, guidance cards, red toast to inform the CMO.
* Mention the optional camera photo log for skin/eye findings.

### 4. Body map (45 s)
* Back on **Body Map**: the body is made of thousands of particles; move the mouse over it to push them.
* The lungs hotspot is now red. Click it — the particles scatter and re-assemble into the lungs.
* Panel explains function, spaceflight effects, hazards, the latest value, actions and its chart.
* Click **Bones & muscles** → exercise chart shows the three missed days (broken treadmill).

### 5. Trends (30 s)
* **Mission calendar** heatmap: the radiation spike on day 12, the fever on days 22–23, the sleep streak.
* Trend alerts: persistent sleep deviation. Radiation panel: cumulative mSv vs. 600 mSv career limit.

### 6. Flight surgeon (30 s)
* Crew table: who needs review and why.
* One-click **downlink report** (Markdown) and CSV export for the next comm pass.

### 7. Wrap-up (15 s)
"Same core logic is exposed via a REST API for wearables and ground systems; switch the environment
to *Mars surface base* and the thresholds and guidance adapt. 59 unit tests cover the logic."
