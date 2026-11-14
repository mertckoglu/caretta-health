"""Question-and-answer triage ("diagnosis") for common spaceflight health problems.

How it works
------------
1. A short decision tree asks one question at a time. The first question screens
   for emergencies, the second asks for the main complaint, then 1–4 follow-ups
   narrow it down.
2. The leaf of the tree is an :class:`Outcome`: the most likely explanation,
   what to do, and who to involve.
3. :func:`assess` cross-checks the outcome against the astronaut's latest
   readings. Out-of-range vitals that matter for that outcome can raise the
   urgency (never lower it) and are listed as evidence.

This is decision support written for a non-specialist crew member, not a
medical diagnosis. The content follows general clinical first-aid logic and
publicly described spaceflight conditions (space motion sickness, SANS, CO₂
exposure, decompression sickness, kidney stones, viral reactivation…).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.core.indicators import INDICATORS
from app.core.thresholds import ENVIRONMENTS, RED, UNKNOWN, YELLOW

# ------------------------------------------------------------------ urgency --
SELF, CMO, SURGEON, EMERGENCY = "self", "cmo", "surgeon", "emergency"
URGENCY_ORDER = [SELF, CMO, SURGEON, EMERGENCY]
URGENCY = {
    SELF: {"label": "Self-care", "who": "You can handle this yourself. Recheck later today.", "color": "#4FD1A5"},
    CMO: {"label": "Tell your CMO today", "who": "Let the crew medical officer know at the next break.", "color": "#EAD94C"},
    SURGEON: {"label": "Flight surgeon review", "who": "Talk to the flight surgeon at the next comm pass.", "color": "#FB923C"},
    EMERGENCY: {"label": "Emergency — act now", "who": "Stop what you are doing, alert the crew and start the emergency checklist.", "color": "#FF7A7A"},
}


def _raise(level: str, to: str) -> str:
    return to if URGENCY_ORDER.index(to) > URGENCY_ORDER.index(level) else level


# --------------------------------------------------------------------- tree --
@dataclass(frozen=True)
class Option:
    label: str
    next: str  # id of a Question or an Outcome


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    options: tuple[Option, ...]
    hint: str = ""


@dataclass(frozen=True)
class Outcome:
    id: str
    title: str
    explanation: str
    urgency: str
    actions: tuple[str, ...]
    check: tuple[str, ...] = ()          # indicators worth looking at for this problem
    hazard: str = ""                     # key of app.core.indicators.HAZARDS
    emergency_if_red: tuple[str, ...] = ()  # a red value here means EMERGENCY


def Q(id: str, text: str, *options: tuple[str, str], hint: str = "") -> Question:  # noqa: N802
    return Question(id, text, tuple(Option(label, nxt) for label, nxt in options), hint)


YES, NO = "Yes", "No"

QUESTIONS: dict[str, Question] = {q.id: q for q in [
    Q("start", "First, is any of this happening right now?",
      ("Severe chest pain or pressure", "x_chest"),
      ("Struggling to breathe, or lips turning blue", "x_breath"),
      ("Fainted, confused or slurring words", "x_neuro"),
      ("Bleeding that won't stop with pressure", "x_bleed"),
      ("None of these", "complaint"),
      hint="If a crewmate can't answer, choose for them."),
    Q("complaint", "What's bothering you the most?",
      ("Headache", "h1"),
      ("Nausea, vomiting or dizziness", "n1"),
      ("Breathing feels off, or a cough", "b1"),
      ("Heart racing or skipping beats", "p1"),
      ("Feverish or generally unwell", "f1"),
      ("Eyes or vision", "e1"),
      ("Back or joint pain", "k1"),
      ("Belly or side pain", "a1"),
      ("Skin problem", "s1"),
      ("Sleep or mood", "m1")),

    # headache
    Q("h1", "Does anyone else have a headache, or does the cabin feel stuffy?",
      (YES, "o_co2"), (NO, "h2"),
      hint="Several people with headaches at once points to the air, not to you."),
    Q("h2", "Has your vision changed — blurry up close, or a shadow somewhere?", (YES, "o_sans"), (NO, "h3")),
    Q("h3", "Are you in the first few days after launch, with a puffy face or blocked nose?",
      (YES, "o_fluid_shift"), (NO, "h4")),
    Q("h4", "Did you sleep under 6 hours, skip a meal or drink less than usual?",
      (YES, "o_tension"), (NO, "o_headache")),

    # nausea / dizziness
    Q("n1", "Did this start within 3 days of launch, landing or another gravity change?", (YES, "n2"), (NO, "n3")),
    Q("n2", "Can you keep fluids down?", (YES, "o_sms"), (NO, "o_sms_severe")),
    Q("n3", "Do you also have fever or diarrhoea, or is a crewmate sick too?", (YES, "o_gi"), (NO, "n4")),
    Q("n4", "Does the room spin when you turn your head, or are your ears ringing?",
      (YES, "o_vestibular"), (NO, "o_nausea")),

    # breathing
    Q("b1", "Does a crewmate feel it too, or is there a CO₂ or air-quality alarm?", (YES, "o_co2_acute"), (NO, "b2")),
    Q("b2", "Did it start after an EVA, a dusty job, or a smell of fumes?", (YES, "o_dust"), (NO, "b3")),
    Q("b3", "Do you have a cough together with a fever?", (YES, "o_chest_infection"), (NO, "o_breathing")),

    # palpitations
    Q("p1", "Did it start during exercise, or after caffeine?", (YES, "p2"), (NO, "p3")),
    Q("p2", "Does it settle within 10 minutes of rest?", (YES, "o_exertional"), (NO, "o_arrhythmia")),
    Q("p3", "Do you feel faint when you stand up or move to a gravity area?", (YES, "o_orthostatic"), (NO, "o_arrhythmia")),

    # fever / unwell
    Q("f1", "Sore throat, runny nose or cough?", (YES, "o_uri"), (NO, "f2")),
    Q("f2", "Burning when you pee, or pain in your side?", (YES, "o_uti"), (NO, "f3")),
    Q("f3", "Cold sores, or a tingling or blistering rash?", (YES, "o_viral_reactivation"), (NO, "o_fever")),

    # eyes
    Q("e1", "Sudden flashes of light, lots of new floaters, or a curtain over part of your vision?",
      (YES, "o_retina"), (NO, "e2"), hint="This one is time-critical, so it comes first."),
    Q("e2", "Is the eye gritty, red or watering — maybe after an EVA or cleaning a filter?",
      (YES, "o_foreign_body"), (NO, "e3")),
    Q("e3", "Is close-up reading blurrier than before the mission?", (YES, "o_sans"), (NO, "o_eye")),

    # back / joints
    Q("k1", "Did the pain start in the 24 hours after an EVA or a cabin pressure change?",
      (YES, "o_dcs"), (NO, "k2"), hint="Joint ache after a pressure change can be decompression sickness."),
    Q("k2", "Is it a dull lower-back ache during your first weeks in weightlessness?",
      (YES, "o_spine"), (NO, "k3")),
    Q("k3", "Did it start while lifting, or on an exercise device?", (YES, "o_strain"), (NO, "o_back")),

    # abdomen
    Q("a1", "Sharp pain in your side or back that comes in waves? Maybe pink or dark urine?",
      (YES, "o_kidney_stone"), (NO, "a2")),
    Q("a2", "Is the pain low on the right, getting worse, and do you feel hot?",
      (YES, "o_appendicitis"), (NO, "a3")),
    Q("a3", "Bloated or constipated, and drinking less than usual?", (YES, "o_constipation"), (NO, "o_abdomen")),

    # skin
    Q("s1", "Is the rash where something touched your skin — electrodes, tape, gloves?",
      (YES, "o_contact"), (NO, "s2")),
    Q("s2", "Sore or cracked fingertips or nails after an EVA?", (YES, "o_glove"), (NO, "s3")),
    Q("s3", "Did it tingle or burn before small blisters showed up?", (YES, "o_viral_reactivation"), (NO, "o_skin")),

    # sleep / mood
    Q("m1", "Is sleep the main problem?", (YES, "m2"), (NO, "m3")),
    Q("m2", "What keeps you awake?",
      ("Noise, light or the work schedule", "o_circadian"), ("My mind won't switch off", "o_stress_sleep")),
    Q("m3", "Over the last two weeks, have you lost interest in things you normally enjoy, or felt hopeless?",
      (YES, "o_depression"), (NO, "m4"),
      hint="Answer honestly. Only you and the medical team see this."),
    Q("m4", "Getting irritated with crewmates more than usual?", (YES, "o_crew_tension"), (NO, "o_low_mood")),
]}


def O(id, title, explanation, urgency, actions, check=(), hazard="", emergency_if_red=()):  # noqa: N802,E741
    return Outcome(id, title, explanation, urgency, tuple(actions), tuple(check), hazard, tuple(emergency_if_red))


OUTCOMES: dict[str, Outcome] = {o.id: o for o in [
    # emergencies
    O("x_chest", "Possible heart emergency",
      "Severe chest pain or pressure needs to be treated as a heart problem until proven otherwise.", EMERGENCY,
      ["Stop all activity and get to the medical area with a crewmate.",
       "Attach the ECG and pulse oximeter, and record blood pressure.",
       "The CMO opens the chest-pain procedure in the medical checklist.",
       "Call the flight surgeon on the emergency loop."],
      check=("heart_rate", "systolic_bp", "spo2"), hazard="gravity"),
    O("x_breath", "Breathing emergency",
      "Severe shortness of breath or blue lips means not enough oxygen is getting through.", EMERGENCY,
      ["Put on an oxygen mask or move to the module with the freshest air flow.",
       "Check the cabin O₂ and CO₂ readings — if others feel it too, suspect the atmosphere.",
       "Measure SpO₂ every 2 minutes.", "Alert the whole crew and the ground."],
      check=("spo2", "heart_rate"), hazard="environment"),
    O("x_neuro", "Possible stroke, head injury or low blood sugar",
      "Fainting, confusion or slurred speech can come from the brain, the heart or very low glucose.", EMERGENCY,
      ["Keep the person still and safe, and don't leave them alone.",
       "Check blood glucose now — if it's under 70 mg/dL and they can swallow, give fast sugar.",
       "Note the exact time symptoms started.", "Alert the crew and the flight surgeon."],
      check=("blood_glucose", "heart_rate", "systolic_bp", "spo2"), hazard="environment"),
    O("x_bleed", "Major bleeding",
      "Bleeding that doesn't stop with firm pressure needs a crewmate's help right away.", EMERGENCY,
      ["Press hard on the wound with gauze, and don't lift it to look.",
       "Raise the injured limb if possible.", "Get the trauma kit and alert the CMO.",
       "Watch for dizziness, pale skin or a racing pulse."],
      check=("heart_rate", "systolic_bp")),

    # headache
    O("o_co2", "Likely CO₂ build-up in the cabin",
      "CO₂ collects in poorly ventilated corners in weightlessness. Headaches in several people at once are a classic sign.",
      CMO,
      ["Check the CO₂ reading on the life-support display.",
       "Move to a well-ventilated module and make sure the fans aren't blocked.",
       "Ask the ground to check the CO₂ scrubber.", "Recheck your headache in 30 minutes."],
      check=("spo2", "heart_rate", "systolic_bp"), hazard="environment"),
    O("o_sans", "Possible eye changes from fluid shift (SANS)",
      "Spaceflight-associated neuro-ocular syndrome can blur near vision. It develops slowly but needs an eye exam.",
      SURGEON,
      ["Do the on-board vision chart test and note the result.",
       "Schedule an eye scan (ultrasound or OCT) with the CMO.",
       "Mention it at the next private medical conference."],
      check=("systolic_bp",), hazard="gravity"),
    O("o_fluid_shift", "Head congestion from fluid shift",
      "In the first days of weightlessness, fluid moves toward the head: puffy face, blocked nose and headache are common.",
      SELF,
      ["Drink regularly, even if you're not thirsty.", "A decongestant from the medical kit can help, per checklist.",
       "It usually eases within a few days."],
      check=("systolic_bp", "heart_rate"), hazard="gravity"),
    O("o_tension", "Tension headache from fatigue, hunger or thirst",
      "The most common headache on a mission. Short sleep, missed meals and low fluid intake all add up.", SELF,
      ["Drink 500 mL of water and eat something.", "Take a 20-minute break away from screens.",
       "A painkiller from the kit is OK per checklist.", "Protect your next sleep period."],
      check=("sleep_hours", "blood_glucose"), hazard="isolation"),
    O("o_headache", "Headache without a clear cause",
      "Nothing obvious explains it yet. Most headaches settle, but a new or unusual one should be logged.", CMO,
      ["Take a painkiller per checklist and rest for 30 minutes.", "Check your blood pressure and temperature.",
       "Tell the CMO if it isn't better in 2 hours or gets worse."],
      check=("systolic_bp", "body_temp", "spo2")),

    # nausea
    O("o_sms", "Space motion sickness",
      "Your inner ear and eyes disagree about which way is up. Most people adapt within 2–3 days.", SELF,
      ["Keep your head still and look at a fixed 'floor' in the module.", "Sip fluids, eat small dry snacks.",
       "Anti-nausea medicine from the kit is fine per checklist.", "Avoid tasks that need lots of head turning today."],
      check=("heart_rate",), hazard="gravity"),
    O("o_sms_severe", "Motion sickness with vomiting",
      "Repeated vomiting quickly leads to dehydration, which makes everything else harder.", CMO,
      ["The CMO can give anti-nausea medicine by injection, per checklist.",
       "Replace fluids with small sips of oral rehydration solution.", "Rest in your sleep station.",
       "Tell the flight surgeon if you can't keep fluids down for 12 hours."],
      check=("heart_rate", "systolic_bp"), hazard="gravity"),
    O("o_gi", "Likely stomach bug",
      "Fever, diarrhoea or a sick crewmate suggest an infection — it spreads easily in a closed cabin.", CMO,
      ["Drink oral rehydration solution little and often.", "Wash hands and wipe shared surfaces.",
       "Use separate utensils and avoid preparing food for others.", "Log your temperature twice a day."],
      check=("body_temp", "heart_rate"), hazard="environment"),
    O("o_vestibular", "Inner-ear (vestibular) problem",
      "Spinning with head movement or ringing ears point to the inner ear.", CMO,
      ["Avoid quick head movements and ladder climbs.", "Don't do EVA or robotics until it settles.",
       "The CMO can do the balance check from the medical checklist."],
      check=("heart_rate", "systolic_bp"), hazard="gravity"),
    O("o_nausea", "Nausea without a clear cause",
      "Could be food, medication, stress or the start of an illness.", CMO,
      ["Eat light, drink small amounts often.", "Check your temperature now and in 4 hours.",
       "Tell the CMO if it lasts more than a day."],
      check=("body_temp", "blood_glucose")),

    # breathing
    O("o_co2_acute", "Possible air-quality problem",
      "If more than one person feels short of breath, the cabin air is the first suspect.", SURGEON,
      ["Check O₂ and CO₂ readings and any life-support alarms.", "Move everyone to the module with the best air flow.",
       "Put on masks if readings are out of range.", "Report to the ground right away."],
      check=("spo2", "heart_rate"), hazard="environment", emergency_if_red=("spo2",)),
    O("o_dust", "Airway irritation from dust or fumes",
      "Lunar and Martian dust is sharp and reactive; fumes from hardware can also irritate the airways.", CMO,
      ["Leave the area and rinse your mouth and nose.", "Check the air-filter status.",
       "Measure SpO₂ now and again in an hour.", "Wear a mask during the next dusty task."],
      check=("spo2",), hazard="environment", emergency_if_red=("spo2",)),
    O("o_chest_infection", "Possible chest infection",
      "A cough with fever can be a lower airway infection — more likely when the immune system is under stress.", SURGEON,
      ["Measure temperature and SpO₂ every 6 hours.", "Rest, drink plenty, and wear a mask around the crew.",
       "The flight surgeon decides whether to start antibiotics from the kit."],
      check=("spo2", "body_temp", "heart_rate"), hazard="radiation", emergency_if_red=("spo2",)),
    O("o_breathing", "Breathlessness without a clear cause",
      "Worth checking properly — it can come from the heart, lungs, anxiety or the air.", CMO,
      ["Measure SpO₂, heart rate and blood pressure.", "Rest for 15 minutes and recheck.",
       "Tell the CMO now if SpO₂ is under 95%."],
      check=("spo2", "heart_rate", "systolic_bp"), emergency_if_red=("spo2",)),

    # palpitations
    O("o_exertional", "Normal fast heartbeat after exertion",
      "A racing heart during exercise or after coffee that settles with rest is expected.", SELF,
      ["Cut back on caffeine today.", "Drink some water.", "Log it if it happens again."],
      check=("heart_rate",), hazard="gravity"),
    O("o_arrhythmia", "Possible heart rhythm problem",
      "A racing or irregular heartbeat that doesn't settle with rest should be recorded on an ECG.", SURGEON,
      ["Sit or strap in and rest.", "Record an ECG while it's happening — that's the most useful data.",
       "Avoid caffeine and strenuous exercise until reviewed.",
       "If you feel faint or get chest pain, treat it as an emergency."],
      check=("heart_rate", "systolic_bp", "spo2"), hazard="gravity"),
    O("o_orthostatic", "Dizziness from low blood volume (orthostatic intolerance)",
      "After time in weightlessness your blood volume drops, so standing up in gravity can make you light-headed.",
      CMO,
      ["Drink 1 L of fluid with salt or electrolyte tablets.", "Stand up slowly, and sit down at the first sign of dizziness.",
       "Wear compression garments if you have them."],
      check=("systolic_bp", "heart_rate"), hazard="gravity"),

    # fever
    O("o_uri", "Common cold or upper airway infection",
      "Most likely a virus. Annoying in a small cabin, but usually harmless.", SELF,
      ["Rest, drink, and log your temperature morning and evening.", "Wash hands often and keep your distance.",
       "Tell the CMO if the fever goes above 38.5 °C or lasts over 3 days."],
      check=("body_temp", "spo2"), hazard="environment"),
    O("o_uti", "Possible urinary or kidney infection",
      "Less fluid and changes in urination in weightlessness make urinary infections more likely.", SURGEON,
      ["Drink extra water.", "The CMO can run a urine test strip from the kit.",
       "The flight surgeon decides on antibiotics."],
      check=("body_temp", "heart_rate"), hazard="gravity"),
    O("o_viral_reactivation", "Possible reactivated virus (cold sores or shingles)",
      "Stress and spaceflight weaken immune control, so dormant viruses like herpes can flare up.", CMO,
      ["Don't touch or scratch the blisters, and wash your hands.", "Take a photo in Check In so it can be tracked.",
       "Antiviral medicine in the kit works best if started early — ask the CMO."],
      check=("body_temp",), hazard="radiation"),
    O("o_fever", "Fever without a clear cause",
      "Your body is fighting something, but it's not clear what yet.", CMO,
      ["Measure temperature every 4 hours.", "Rest, drink and eat light.",
       "Watch for new symptoms: cough, rash, pain when peeing.", "The CMO can give a fever reducer per checklist."],
      check=("body_temp", "heart_rate", "spo2")),

    # eyes
    O("o_retina", "Possible retinal problem",
      "Sudden flashes, a burst of floaters or a curtain over vision can be a retinal tear or detachment.", EMERGENCY,
      ["Stop work and rest with your head still.", "Don't rub the eye.",
       "Talk to the flight surgeon right away — this is time-critical."],
      check=("systolic_bp",)),
    O("o_foreign_body", "Something in the eye",
      "Floating dust and debris don't fall out of the eye in weightlessness the way they would on Earth.", SELF,
      ["Rinse with the eyewash from the kit, eye open.", "Don't rub.",
       "Tell the CMO if it still hurts after rinsing or vision is blurry."],
      hazard="environment"),
    O("o_eye", "Eye discomfort without a clear cause",
      "Dry cabin air and screen time are common culprits.", SELF,
      ["Use lubricating eye drops.", "Take regular breaks from screens.",
       "Tell the CMO if it doesn't improve within a day."],
      hazard="environment"),

    # back / joints
    O("o_dcs", "Possible decompression sickness (the bends)",
      "Nitrogen bubbles can form after a pressure drop, usually causing a deep ache in a joint.", EMERGENCY,
      ["Tell the crew immediately — this is treated with pressure.",
       "Breathe 100% oxygen if available.", "Follow the decompression sickness procedure in the EVA checklist.",
       "Contact the flight surgeon now."],
      check=("spo2", "heart_rate")),
    O("o_spine", "Back pain from spinal lengthening",
      "Without gravity your spine stretches by a few centimetres, which often causes lower-back ache early on.", SELF,
      ["Pull your knees to your chest (fetal position) for a few minutes.", "Gentle stretching helps.",
       "A painkiller from the kit is fine per checklist."],
      check=("exercise_minutes",), hazard="gravity"),
    O("o_strain", "Muscle strain",
      "Most likely a pulled muscle from lifting or exercising.", SELF,
      ["Rest it today and use a cold pack.", "Ask the CMO to check your form on the exercise device.",
       "Tell the CMO if you feel numbness or weakness in a leg."],
      check=("exercise_minutes",), hazard="gravity"),
    O("o_back", "Back or joint pain without a clear cause",
      "Worth keeping an eye on, especially if it gets worse.", CMO,
      ["Use a painkiller per checklist.", "Log where it hurts and how bad it is (0–10).",
       "Tell the CMO about numbness, weakness or problems peeing."],
      check=("body_temp",)),

    # abdomen
    O("o_kidney_stone", "Possible kidney stone",
      "Bone loss in weightlessness releases calcium into the urine, so kidney stones are a known spaceflight risk.",
      SURGEON,
      ["Drink plenty of water.", "Take painkillers per checklist.", "Strain your urine if the kit allows.",
       "Fever with this pain needs the flight surgeon right away."],
      check=("body_temp", "heart_rate"), hazard="gravity"),
    O("o_appendicitis", "Possible appendicitis",
      "Lower-right belly pain that keeps getting worse, with fever, needs a medical assessment quickly.", EMERGENCY,
      ["Don't eat, and only take small sips of water.", "The CMO performs the abdominal exam from the checklist.",
       "Contact the flight surgeon now."],
      check=("body_temp", "heart_rate")),
    O("o_constipation", "Constipation",
      "Very common in space: less fluid, less fibre and less movement.", SELF,
      ["Drink more water and eat the high-fibre menu items.", "Keep up your daily exercise.",
       "A mild laxative from the kit is fine per checklist."],
      check=("exercise_minutes",), hazard="gravity"),
    O("o_abdomen", "Belly pain without a clear cause",
      "Might be gas or food, but should be watched.", CMO,
      ["Log where it hurts and how bad it is (0–10).", "Check your temperature.",
       "Tell the CMO if it gets worse, or you get fever or vomiting."],
      check=("body_temp", "heart_rate")),

    # skin
    O("o_contact", "Contact dermatitis",
      "Skin reacting to something that touched it, like electrode gel, tape or glove material.", SELF,
      ["Remove the source and wash the area.", "Use the hydrocortisone cream from the kit.",
       "Take a photo in Check In to compare tomorrow."],
      hazard="environment"),
    O("o_glove", "EVA glove injury",
      "Pressurised gloves can bruise or lift fingernails and crack the skin on the fingertips.", CMO,
      ["Keep the area clean and dry, and use a protective dressing.", "Take a photo in Check In.",
       "Tell the CMO before your next EVA — glove fit may need changing."]),
    O("o_skin", "Skin problem without a clear cause",
      "Dry air and less frequent washing often irritate the skin in space.", SELF,
      ["Moisturise twice a day.", "Take a photo in Check In so you can see if it's changing.",
       "Tell the CMO if it spreads, oozes or comes with fever."],
      check=("body_temp",), hazard="environment"),

    # sleep / mood
    O("o_circadian", "Sleep disrupted by schedule, light or noise",
      "Sunrises every 90 minutes in orbit, fan noise and shifting schedules all confuse your body clock.", SELF,
      ["Use the eye mask and earplugs.", "Keep the same sleep window every day where possible.",
       "Use the bright 'daytime' lighting after waking and dim light an hour before bed."],
      check=("sleep_hours", "mood"), hazard="isolation"),
    O("o_stress_sleep", "Stress keeping you awake",
      "A racing mind at bedtime is common on demanding missions.", SELF,
      ["Write tomorrow's worries down before bed.", "Try 10 minutes of slow breathing or a guided relaxation.",
       "Talk to someone if it continues for more than a few nights."],
      check=("sleep_hours", "mood"), hazard="isolation"),
    O("o_depression", "Possible low mood or depression",
      "Losing interest and feeling hopeless for two weeks is more than a bad day. It's common, treatable, and nothing to be ashamed of.",
      SURGEON,
      ["Book a private conference with the behavioural health team.",
       "Tell one crewmate you trust how you've been feeling.",
       "Keep your exercise and sleep routine — both protect mood.",
       "If you have thoughts of harming yourself, tell the CMO now."],
      check=("mood", "sleep_hours"), hazard="isolation"),
    O("o_crew_tension", "Friction within the crew",
      "Months in a small space wear on everyone. Irritability is often an early warning sign of fatigue.", SELF,
      ["Take some time alone — music, a call home, the window.", "Raise small issues early, calmly and in private.",
       "The behavioural health team can help with crew conversations."],
      check=("sleep_hours", "mood"), hazard="isolation"),
    O("o_low_mood", "Feeling flat",
      "Short dips in mood are normal, especially in the second half of a mission.", SELF,
      ["Plan something to look forward to this week.", "Call family or a friend.",
       "Keep moving — exercise reliably lifts mood."],
      check=("mood", "sleep_hours"), hazard="isolation"),
]}

START = "start"


# ------------------------------------------------------------------ engine --
def node(node_id: str) -> Question | Outcome:
    if node_id in QUESTIONS:
        return QUESTIONS[node_id]
    if node_id in OUTCOMES:
        return OUTCOMES[node_id]
    raise KeyError(f"unknown triage node {node_id!r}")


def walk(answers: list[int]) -> tuple[list[tuple[Question, Option]], Question | Outcome]:
    """Follow ``answers`` (option indexes) from the start. Returns the answered steps and the current node."""
    steps: list[tuple[Question, Option]] = []
    current: Question | Outcome = QUESTIONS[START]
    for idx in answers:
        if not isinstance(current, Question):
            raise ValueError("too many answers: the triage already reached an outcome")
        if not 0 <= idx < len(current.options):
            raise ValueError(f"answer {idx} is not valid for question {current.id!r}")
        opt = current.options[idx]
        steps.append((current, opt))
        current = node(opt.next)
    return steps, current


def max_depth() -> int:
    def depth(nid: str) -> int:
        n = node(nid)
        return 0 if isinstance(n, Outcome) else 1 + max(depth(o.next) for o in n.options)
    return depth(START)


@dataclass
class Assessment:
    outcome_id: str
    title: str
    explanation: str
    urgency: str
    base_urgency: str
    actions: list[str]
    evidence: list[dict] = field(default_factory=list)
    answers: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def urgency_label(self) -> str:
        return URGENCY[self.urgency]["label"]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["urgency_label"] = self.urgency_label
        return d


def assess(answers: list[int], statuses: dict | None = None, environment: str = "iss") -> Assessment:
    """Run the triage and cross-check the result with the latest readings.

    ``statuses`` is the ``indicator -> IndicatorStatus`` dict from :func:`app.core.status.evaluate_latest`.
    """
    steps, current = walk(answers)
    if not isinstance(current, Outcome):
        raise ValueError("the triage is not finished yet")
    out = current
    urgency = out.urgency
    evidence, notes = [], []
    statuses = statuses or {}

    for key in out.check:
        s = statuses.get(key)
        if s is None or s.status == UNKNOWN:
            evidence.append({"indicator": key, "name": INDICATORS[key].name, "value": "not measured",
                             "status": UNKNOWN})
            continue
        evidence.append({"indicator": key, "name": INDICATORS[key].name,
                         "value": INDICATORS[key].format(s.value), "status": s.status})
        if s.status == RED:
            if key in out.emergency_if_red:
                urgency = _raise(urgency, EMERGENCY)
                notes.append(f"{INDICATORS[key].name} is in the red zone, so this is treated as an emergency.")
            else:
                urgency = _raise(urgency, SURGEON)
                notes.append(f"{INDICATORS[key].name} is in the red zone — the flight surgeon should review this.")
        elif s.status == YELLOW:
            urgency = _raise(urgency, CMO)
            notes.append(f"{INDICATORS[key].name} is outside the normal range — mention it to your CMO.")

    missing = [e["name"] for e in evidence if e["status"] == UNKNOWN]
    if missing:
        notes.append("Measuring " + ", ".join(missing) + " would make this assessment more reliable.")

    lo, hi = ENVIRONMENTS.get(environment, {}).get("one_way_delay_min", (0, 0))
    if hi >= 1 and URGENCY_ORDER.index(urgency) >= URGENCY_ORDER.index(SURGEON):
        notes.append(f"Messages to Earth take {lo:g}–{hi:g} minutes each way here. Don't wait for an answer — "
                     "start the on-board steps with your CMO now.")

    return Assessment(
        outcome_id=out.id,
        title=out.title,
        explanation=out.explanation,
        urgency=urgency,
        base_urgency=out.urgency,
        actions=list(out.actions),
        evidence=evidence,
        answers=[{"question": q.text, "answer": o.label} for q, o in steps],
        notes=notes,
    )


def summary_line(a: Assessment) -> str:
    return f"{a.title} — {a.urgency_label}"
