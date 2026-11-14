# 🐢 Caretta — astronaut health self-assessment

> Like the loggerhead sea turtle (*Caretta caretta*) that carries its shelter across oceans, Caretta is a
> health companion astronauts carry far from Earth: **measure → understand → act → escalate when needed.**

Caretta is a visual tool that helps astronauts assess their own health during space missions and gives
plain-language guidance on what to do next. It was built for the NASA Space Apps challenge on astronaut
self-assessment and is grounded in NASA's Human Research Program (HRP) five hazards of human spaceflight.

![status](https://img.shields.io/badge/tests-59%20passing-2E9D5B) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

## Features

| Challenge objective | How Caretta does it |
|---|---|
| Collect health data from the user | Guided **check-in**: type any of the 10 indicators (empty fields are skipped, status shows while typing), emoji mood buttons, and **photos** from the camera or upload (rash, wound, eye…) saved to the **Gallery**. REST API for wearables and onboard devices. |
| Clear presentation & diagnosis | **Traffic-light status** (colour + shape + words, colour-blind safe) per indicator, per body system and overall. |
| Interactive human figure | **Animated particle body map**: ~6–14k particles form a realistic human figure; click a body system and they scatter and re-assemble into the brain, heart, lungs, abdominal organs, lymphatic system, skeleton or a radiation view. Each system shows its function, spaceflight effects, hazards, latest values, guidance and a trend chart. |
| Dynamic charts over time | Indicator charts with green/yellow/red bands and 7-day averages, a **mission calendar heatmap**, radiation dose (daily + cumulative vs. 600 mSv career limit). |
| Guidance on treatments & improvements | Specific actions for every indicator × direction × severity and **who acts** (self, crew medical officer, flight surgeon). |
| When to involve crew / flight surgeon | Escalation rules + trend engine (persistence, sleep debt, heart-rate drift, low mood, cumulative dose) and a one-click **downlink report**. |
| Prompt measurements as a routine | **Daily routine** with due/upcoming tasks. |
| Gamification | XP, levels (Cadet → Chief Astronaut), check-in streaks and badges. |
| Different environments | Space station, deep-space transit, lunar base, Mars base, rover. **Each environment is its own mission dataset**, simulated automatically the first time it is opened with environment-specific physiology and events (no-magnetosphere SPE in transit, lunar dust & lunar night, Mars comm delay & dust storm, rover EVAs & cabin CO₂). Radiation/exercise limits and communication-delay guidance adapt too. |
| Don't assume medical knowledge | "How to measure" and "Why it matters" cards for every indicator, including microgravity tips. |

### Indicators

Resting heart rate · systolic/diastolic blood pressure · SpO₂ · body temperature · fasting blood glucose ·
sleep hours · mood (1–5) · countermeasure exercise minutes · radiation dose (24 h).
Thresholds and sources: [`data/thresholds_sources.md`](data/thresholds_sources.md).
Hazard → body system → indicator mapping: [`docs/hazards_to_systems.md`](docs/hazards_to_systems.md).

## Quick start

```bash
git clone <this-repo> caretta && cd caretta
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Web app (seeds a 30-day demo mission on first start)
streamlit run app/ui/Home.py                          # → http://localhost:8501

# REST API (optional)
uvicorn app.api.main:app --reload                     # → http://localhost:8000/docs

# Tests
pytest -q
```

Data is stored in SQLite at `data/caretta.db` (override with the `CARETTA_DB` environment variable).
Both the UI and the API use the same database.

### Demo data

```bash
python scripts/seed_demo_data.py --db --reset                                   # 4-person crew, ends today
python scripts/seed_demo_data.py --db --reset --environment mars_base           # Mars surface
python scripts/seed_demo_data.py --from-csv data/sample_mission_30d.csv --db --reset   # shipped CSV, shifted to today
```

`data/sample_mission_30d.csv` is a reproducible 30-day ISS mission for the commander with a solar
particle event (day 12), a broken treadmill (days 16–18), a fever (days 22–23), a mid-mission mood dip and
gradual sleep erosion. The walkthrough is in [`docs/demo-script.md`](docs/demo-script.md).

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/indicators?environment=iss` | Indicator catalogue with thresholds and measuring instructions |
| GET | `/hazards`, `/regions`, `/environments` | Reference data |
| POST | `/readings` | Add a reading → returns it with its status (201) |
| GET | `/readings?astronaut_id=CDR&indicator=&days=30` | List readings |
| DELETE | `/readings/{id}` | Delete a reading |
| GET | `/astronauts` | Crew members with data |
| GET | `/status/{astronaut_id}?environment=iss` | Full assessment: overall, per indicator, per body region, trend alerts, recommendations, escalation |
| GET | `/recommendations/{astronaut_id}` | Prioritised guidance |
| GET | `/report/{astronaut_id}` | Markdown downlink report for the flight surgeon |
| POST | `/simulate` | Generate a synthetic mission for an astronaut |

```bash
curl -X POST localhost:8000/readings -H 'Content-Type: application/json' \
     -d '{"astronaut_id":"CDR","indicator":"spo2","value":91}'
# → {"id":1, ..., "status":"red"}
```

## Project structure

```
app/
  core/            pure Python domain logic (no UI, fully unit-tested)
    indicators.py  indicators, NASA HRP hazards, body regions, measuring instructions
    thresholds.py  green/yellow/red bands, environment overrides, classify()
    status.py      latest status, body-region status, trend alerts, escalation
    recommend.py   guidance, daily routine, XP/levels/badges, downlink report
    simulate.py    synthetic but plausible mission data with scripted events
  api/             FastAPI service + SQLite storage (db.py, schemas.py, main.py)
  ui/              Streamlit multipage app
    Home.py        dashboard   ·  pages/1_Check_In.py  ·  2_Body_Map.py
    body_map.py    particle body component wrapper ·  3_Trends.py  ·  4_Flight_Surgeon.py
    particle_body/ index.html — Canvas particle engine (no build step, Streamlit component)
    charts.py      status chips/cards and charts    ·  4_Gallery.py  ·  5_About.py
data/              sample mission CSV + threshold sources
docs/              hazard mapping, demo script
scripts/           demo data generator / loader
tests/             pytest suite (core, simulation, API)
```

## Design notes

* **Offline first** — a single SQLite file, no cloud dependency: crews beyond LEO can't rely on a link to Earth.
* **Trends over single readings** — persistent deviations matter more than one bad number.
* **Accessible status** — every colour is paired with a shape (● ▲ ■) and a word; the body map has a keyboard-friendly list alternative.
* **Separation of concerns** — all medical logic is in `app/core`, shared by the UI and the API and covered by tests.

## Disclaimer

Caretta is a hackathon prototype for education and decision support. It is **not a medical device** and does
not diagnose. Thresholds are simplified screening limits. Always follow mission medical procedures and the
instructions of your flight surgeon.

## License

[MIT](LICENSE)
