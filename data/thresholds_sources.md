# Thresholds and their sources

Caretta uses a three-zone traffic light per indicator. Bands are half-open intervals `[low, high)`.
Anything outside the green and yellow bands (but still physically plausible) is red.
The limits are **screening limits for healthy, medically selected adults**, intentionally simple so an
astronaut can act on them without medical training. They are *not* diagnostic criteria and were chosen
for a hackathon prototype; a flight medicine team would personalise them per crew member.

The single source of truth in code is `app/core/thresholds.py`.

| Indicator | Unit | 🟢 Green | 🟡 Yellow | 🔴 Red | Rationale / source |
|---|---|---|---|---|---|
| Resting heart rate | bpm | 50–100 | 40–50, 100–120 | < 40, ≥ 120 | Adult resting range 60–100 bpm (AHA); fit astronauts often sit at 50–60, so the green floor is 50. |
| Systolic BP | mmHg | 90–130 | 85–90, 130–160 | < 85, ≥ 160 | 2017 ACC/AHA guideline: < 120 normal, 120–129 elevated, ≥ 130 hypertension. Simplified: elevated stays green; stage 1/2 → watch; ≥ 160 → act. |
| Diastolic BP | mmHg | 60–80 | 55–60, 80–100 | < 55, ≥ 100 | 2017 ACC/AHA: ≥ 80 stage 1, ≥ 90 stage 2. |
| SpO₂ | % | ≥ 95 | 92–95 | < 92 | Normal 95–100 %; values < 92 % at rest usually prompt clinical evaluation (BTS oxygen guideline target 94–98 %). |
| Body temperature | °C | 36.1–37.5 | 35.5–36.1, 37.5–38.0 | < 35.5, ≥ 38.0 | Fever ≥ 38.0 °C (100.4 °F, CDC definition). Hypothermia < 35 °C; we flag earlier. |
| Fasting glucose | mg/dL | 70–100 | 54–70, 100–180 | < 54, ≥ 180 | ADA Standards of Care: normal fasting 70–99, prediabetes 100–125, level-1 hypoglycaemia < 70, level-2 < 54. |
| Sleep (24 h) | h | 7–9.5 | 5.5–7, 9.5–11 | < 5.5, ≥ 11 | AASM/SRS consensus: adults need ≥ 7 h. NASA schedules 8.5 h sleep periods on the ISS. |
| Mood | 1–5 | 4–5 | 2–3 | 1 | Self-rating; low mood for several days triggers a trend alert (behavioural-health risk, NASA HRP). |
| Countermeasure exercise | min/day | ≥ 90 (ISS) | 30–90 | < 30 | ISS crews exercise ~2 h/day (ARED + treadmill + cycle). Lower targets on surfaces/rovers where partial gravity provides some loading. |
| Radiation dose (24 h) | mSv | < 1.0 (ISS) | 1–5 | ≥ 5 | ISS typical 0.3–0.8 mSv/day. A jump to several mSv in a day indicates a solar particle event → shelter. |

## Environment overrides

| Environment | Radiation green / yellow (mSv/day) | Exercise green (min) | Typical dose used by the simulator |
|---|---|---|---|
| Space station (LEO) | < 1.0 / 1–5 | ≥ 90 | 0.5 mSv/day |
| Deep-space transit | < 2.5 / 2.5–10 | ≥ 60 | 1.8 mSv/day (MSL/RAD cruise measurement, Zeitlin et al., *Science* 2013) |
| Lunar surface base | < 2.0 / 2–10 | ≥ 60 | 1.3 mSv/day (Chang'e-4 LND, Zhang et al., *Science Advances* 2020) |
| Mars surface base | < 1.0 / 1–5 | ≥ 60 | 0.7 mSv/day (Curiosity RAD, Hassler et al., *Science* 2014) |
| Pressurised rover | < 2.0 / 2–10 | ≥ 30 | 1.3 mSv/day |

## Trend rules (`app/core/status.py::detect_trends`)

* **Persistence** – an indicator out of the green zone 3 days in a row → yellow; 7+ days → red.
* **Sleep debt** – 7-day average < 6 h → yellow, < 5 h → red.
* **Heart-rate drift** – mean of the last 3 days > 115 % of the first-week baseline → yellow.
* **Low mood** – 3-day average ≤ 2.5 → yellow.
* **Cumulative dose** – ≥ 50 % of the NASA career limit → yellow, ≥ 80 % → red.

## Escalation to the flight surgeon (`needs_flight_surgeon`)

Any red reading, any red trend, or three or more simultaneous yellow readings.

## References

1. NASA Human Research Program — *The Human Body in Space* and the five hazards of human spaceflight. https://www.nasa.gov/hrp/
2. NASA-STD-3001, *Space Flight Human-System Standard*, Vol. 1 Rev. B (2022) — career effective dose limit 600 mSv.
3. Whelton P.K. et al. *2017 ACC/AHA Guideline for the Prevention, Detection, Evaluation, and Management of High Blood Pressure in Adults.* Hypertension 71(6), 2018.
4. American Diabetes Association. *Standards of Care in Diabetes* — Classification and Diagnosis; Glycemic Goals and Hypoglycemia.
5. Watson N.F. et al. *Recommended Amount of Sleep for a Healthy Adult* (AASM/SRS consensus). Sleep 38(6), 2015.
6. O'Driscoll B.R. et al. *BTS guideline for oxygen use in healthcare and emergency settings.* Thorax 72, 2017.
7. Zeitlin C. et al. *Measurements of energetic particle radiation in transit to Mars on the Mars Science Laboratory.* Science 340, 2013.
8. Hassler D.M. et al. *Mars' surface radiation environment measured with the Mars Science Laboratory's Curiosity rover.* Science 343, 2014.
9. Zhang S. et al. *First measurements of the radiation dose on the lunar surface.* Science Advances 6(39), 2020.
10. Bechtel R.B., Berning A. *The third-quarter phenomenon: do people experience discomfort after stress has passed?* In: From Antarctica to Outer Space, Springer, 1991.
11. ESA / CSA / JAXA astronaut health pages for exercise countermeasures and bone loss (~1–1.5 % per month in weight-bearing bones).
