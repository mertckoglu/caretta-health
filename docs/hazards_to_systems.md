# From spaceflight hazards to indicators

NASA's Human Research Program groups the risks of human spaceflight into five hazards
(**RIDGE**: Radiation, Isolation & confinement, Distance from Earth, Gravity fields, hostile/closed
Environment). Caretta maps each hazard to the body systems it affects and to an indicator the
astronaut can measure on board with simple equipment.

```
Hazard                     Body system (body map)       Indicator(s)                     On-board tool
-------------------------  ---------------------------  -------------------------------  ----------------------------
☢️ Radiation               Whole body, immune           Radiation dose (24 h)            Personal active dosimeter
                                                        Body temperature                 Thermometer
🧠 Isolation & confinement  Brain & behaviour            Sleep hours, mood                Actigraphy watch, self-rating
📡 Distance from Earth      Brain & behaviour            Mood                             Self-rating
                           (all systems: autonomy)      → drives escalation logic
🪐 Gravity fields           Heart & vessels              Heart rate, blood pressure       Wrist monitor, BP cuff
                           Bones & muscles              Countermeasure exercise minutes  Exercise device log
                           Metabolism                   Fasting blood glucose            Glucometer
🛰️ Hostile environment      Lungs                        SpO₂                             Pulse oximeter
                           Immune                       Body temperature                 Thermometer
```

## Why these indicators?

| Question from the challenge | Caretta's answer |
|---|---|
| *Which measurements can be performed in space?* | All ten indicators use small, already-flown devices (cuff, oximeter, thermometer, glucometer, actigraphy, dosimeter) or a self-rating. Each has a step-by-step "How to measure" card, including microgravity tips (foot loops, capturing the blood drop). |
| *Why is an exam needed?* | Effects are slow (bone loss, deconditioning, sleep debt) or sudden (solar particle event, infection). Daily self-checks catch both; the trend engine turns slow drifts into alerts. |
| *How do hazards affect indicators?* | See the table above, the body-map "In space" text and `app/core/indicators.py`. |
| *When does a result need the crew or flight surgeon?* | Yellow → self-care and re-measure; SpO₂/temperature yellow → crew medical officer; any red, red trend or ≥ 3 yellows → flight surgeon (downlink report). |
| *What actions prevent a critical condition?* | Every indicator × direction × severity has concrete actions in `app/core/recommend.py::GUIDANCE` (hydrate, shelter, eat 15 g carbs, protect sleep, talk to someone, …). |

## Environment awareness

The same reading can mean different things in different places. Caretta's environment selector
(space station, deep-space transit, lunar base, Mars base, rover) changes the radiation and exercise
targets and the context notes — e.g. on Mars the one-way communication delay of 4–24 minutes means the
on-board guidance must be enough to act on before ground can respond.
