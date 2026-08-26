#!/usr/bin/env python3
"""Generate a synthetic multi-disease patient dataset (hackathon-sammz).

500 records across 11 diseases, ALL AGES (infants to 86+), split across
three hospital sites for the Rare Disease Consult Network demo.

Per-site files (data/sites/site_*.jsonl) match PLAN.md exactly:

    {
      "record_id": "7F3A2C91",
      "disease": "community_acquired_pneumonia",
      "symptoms": ["productive_cough", "fever", ...],
      "gender": "M",
      "age_bracket": "51-65",
      "race": "White",
      "height_bracket": "170-179cm",
      "weight_bracket": "80-89kg",
      "text": "<free-text ED clerking note>"
    }

The combined files additionally carry a "site" field (A/B/C).

Narrative seeding: kawasaki_disease has exactly 3 cases — 1 at site B,
2 at site C, none at site A — the "split case" the demo needs.

All data is synthetic. Not real patients. No clinical use.

Usage:
    python3 generate_dataset.py [--seed S] [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

DEFAULT_SEED = 20260826

AGE_BRACKETS = [
    (0, 2, "0-2"), (3, 5, "3-5"), (6, 11, "6-11"), (12, 17, "12-17"),
    (18, 30, "18-30"), (31, 40, "31-40"), (41, 50, "41-50"),
    (51, 65, "51-65"), (66, 75, "66-75"), (76, 85, "76-85"), (86, 95, "86+"),
]
PEDS_AGE_WEIGHTS = [20, 20, 30, 30]            # 0-2, 3-5, 6-11, 12-17
ADULT_AGE_WEIGHTS = [8, 10, 14, 26, 22, 14, 6]  # 18-30 ... 86+
RACES = [("White", 62), ("Black", 14), ("Asian", 12), ("Hispanic", 9), ("Mixed/Other", 3)]
SITES = ["A", "B", "C"]

ADULT_COMORBIDS = {
    "hypertension": 0.30, "type 2 diabetes": 0.22, "COPD": 0.14,
    "ischaemic heart disease": 0.12, "chronic kidney disease stage 3": 0.08,
    "atrial fibrillation": 0.08, "heart failure": 0.06,
}
PEDS_PMH = [
    "Born at term, normal delivery, immunisations up to date; no past medical history.",
    "Ex-full-term infant, immunisations up to date, no regular medications.",
    "Mild asthma on salbutamol PRN; otherwise well, immunisations up to date.",
    "No significant history; developmentally appropriate for age.",
]

# ---------------------------------------------------------------- symptom vocabulary
SYMPTOM_PHRASES = {
    "fever": ["fever", "high temperature", "fevers at home"],
    "productive_cough": [None],  # built with a sputum colour
    "dry_cough": ["dry cough", "persistent dry cough"],
    "dyspnea": ["breathlessness", "shortness of breath on exertion, now at rest", "increasing breathlessness"],
    "wheeze": ["wheeze", "wheezy breathing"],
    "chest_tightness": ["chest tightness"],
    "pleuritic_chest_pain": ["pleuritic chest pain", "sharp chest pain worse on inspiration"],
    "fatigue_malaise": ["malaise", "fatigue", "generalised malaise"],
    "myalgia": ["generalised myalgia"],
    "arthralgia": ["joint pains"],
    "chills_sweats": ["chills", "drenching night sweats", "chills and sweats"],
    "rigors": ["rigors"],
    "anorexia": ["reduced appetite"],
    "headache": ["headache"],
    "sore_throat": ["sore throat"],
    "nausea_vomiting": ["nausea and occasional vomiting"],
    "diarrhea": ["loose stools"],
    "poor_feeding": ["poor feeding", "feeding at half usual volumes"],
    "irritability": ["irritability", "unusual irritability"],
    "confusion": [None],  # handled with dedicated sentences
    "rash": ["a widespread rash", "a polymorphous rash", "an erythematous rash"],
    "conjunctival_injection": ["red eyes", "bilateral red eyes without discharge"],
    "red_cracked_lips": ["red, cracked lips"],
    "strawberry_tongue": ["a strawberry tongue"],
    "swollen_hands_feet": ["swollen, red hands and feet"],
    "cervical_lymphadenopathy": ["a swollen gland in the neck", "enlarged cervical lymph nodes"],
    "neck_stiffness": ["neck stiffness"],
    "photophobia": ["photophobia"],
    "abdominal_pain": ["abdominal pain"],
    "limb_weakness": ["progressive limb weakness", "leg weakness ascending over days"],
    "paresthesia": ["tingling in the hands and feet"],
    "back_pain": ["back pain"],
    "unilateral_leg_swelling": ["one-sided calf swelling and tenderness"],
    "hemoptysis": ["blood-streaked sputum"],
    "palpitations": ["palpitations"],
    "syncope": ["a blackout", "a collapse"],
    "periorbital_edema": ["puffy eyes and facial swelling"],
    "oliguria": ["reduced urine output"],
    "frothy_urine": ["frothy urine"],
}
SPUTUM_COLORS = ["green", "yellow", "yellow-green", "mucopurulent", "rusty"]

CXR_ZONES = {
    "right lower lobe": "right base", "left lower lobe": "left base",
    "right upper lobe": "right upper zone", "right middle lobe": "right mid zone",
    "left upper lobe": "left upper zone", "bilateral": "both bases",
}
CXR_SITES = [("right lower lobe", 30), ("left lower lobe", 25), ("right upper lobe", 10),
             ("right middle lobe", 10), ("left upper lobe", 7), ("bilateral", 18)]

ADULT_OPENERS = [
    "{age}-year-old {person} presented to the emergency department with a {dur}-day history of {main}.",
    "{person_c} aged {age} is referred by the GP with a {dur}-day history of {main}.",
    "ED clerking: {age}-year-old {person} reporting {dur} days of {main}.",
]
PEDS_OPENERS = [
    "{age_str} {person} brought in by {carer} with a {dur}-day history of {main}.",
    "Paediatric ED: {age_str} {person}, {carer} reports {dur} days of {main}.",
]
CONFUSION_HPI = [
    "Family report new-onset confusion since last night.",
    "There is a history of new-onset confusion per the care home staff.",
    "The patient has been mildly confused at home over the past 24 hours.",
]

# ---------------------------------------------------------------- diseases
# ages: ("mixed", p_peds) | ("peds", lo, hi) | ("adult", lo, hi) | ("any", lo, hi)
# findings may use {zone} (CAP) or {rash_clause} (meningitis);
# ix/assessment are format strings resolved against the case dict.
DISEASES = {
    "community_acquired_pneumonia": {
        "count": 210, "ages": ("mixed", 0.22),
        "symptoms": {
            "productive_cough": 0.85, "fever": 0.80, "dyspnea": 0.72,
            "fatigue_malaise": 0.60, "chills_sweats": 0.40,
            "pleuritic_chest_pain": 0.35, "myalgia": 0.30, "rigors": 0.30,
            "anorexia": 0.25, "headache": 0.20, "wheeze": 0.15,
            "nausea_vomiting": 0.15, "diarrhea": 0.10,
            "poor_feeding": 0.30, "irritability": 0.25,
        },
        "core": ["productive_cough", "fever", "dyspnea"],
        "findings": [
            "Focal coarse crackles with increased vocal resonance at the {zone}.",
            "Bronchial breathing and crackles over the {zone}.",
            "Reduced chest expansion and dullness at the {zone} with audible crackles.",
        ],
        "ix": "CXR: {cxr_desc}. Bloods: WCC {wcc}, CRP {crp} mg/L, urea {urea} mmol/L; blood cultures sent.",
        "assessment": "community-acquired pneumonia ({cxr_desc}){curb_str} - {severity} severity.",
        "plans": {
            "mild": [
                "Discharged with oral amoxicillin 500 mg TDS for 5 days, simple analgesia, and GP review in 48 hours; repeat CXR in 6 weeks.",
                "Discharged on doxycycline 100 mg OD for 7 days with written safety-netting advice.",
                "Admitted overnight for observation, IV fluids and antibiotics, likely step-down to orals tomorrow.",
            ],
            "moderate": [
                "Admitted to the acute medical ward: IV amoxicillin/clavulanate 1.2 g TDS plus oral clarithromycin 500 mg BD, nebulised salbutamol and IV fluids.",
                "Admitted under the medical team: treated as moderate CAP with IV co-amoxiclav and clarithromycin; VTE prophylaxis and early mobilisation planned.",
            ],
            "severe": [
                "Referred to critical care: IV piperacillin/tazobactam plus clarithromycin, controlled oxygen therapy, aggressive IV fluids; discussed with the ICU registrar.",
                "Managed in HDU: sepsis six initiated with IV piperacillin/tazobactam and clarithromycin; close monitoring of lactate and urine output.",
            ],
        },
        "plans_peds": {
            "mild": ["Discharged on oral amoxicillin 40 mg/kg/day in three divided doses for 5 days; caregiver advice on fluids, antipyretics and red-flag symptoms."],
            "moderate": ["Admitted to the paediatric ward: nasal suction, oxygen to keep SpO2 above 92%, IV amoxicillin 25 mg/kg TDS and maintenance fluids."],
            "severe": ["Transferred to PICU: high-flow nasal cannula oxygen, IV co-amoxiclav, continuous cardiorespiratory monitoring."],
        },
    },

    "influenza": {
        "count": 66, "ages": ("mixed", 0.20),
        "symptoms": {
            "fever": 0.95, "myalgia": 0.80, "dry_cough": 0.70, "fatigue_malaise": 0.80,
            "headache": 0.60, "sore_throat": 0.60, "chills_sweats": 0.50,
            "anorexia": 0.40, "nausea_vomiting": 0.25,
            "poor_feeding": 0.30, "irritability": 0.30,
        },
        "core": ["fever"],
        "findings": [
            "Coryzal, pharyngeal erythema, chest clear on auscultation.",
            "Flushed, mildly injected conjunctivae, tender muscles on palpation; chest clear.",
        ],
        "ix": "Nasopharyngeal swab: influenza A positive. Bloods: WCC {wcc}, CRP {crp} mg/L.",
        "assessment": "influenza A - {severity}.",
        "plans": {
            "mild": ["Discharged with antipyretics, fluids and isolation advice; antivirals withheld (low risk).",
                     "Discharged on oseltamivir 75 mg BD for 5 days given comorbidity; public health notified."],
            "moderate": ["Admitted for IV fluids and oseltamivir; monitoring for secondary bacterial infection."],
            "severe": ["Managed in HDU: oseltamivir and oxygen therapy for influenza pneumonitis; bacterial superinfection screened."],
        },
        "plans_peds": {
            "mild": ["Discharged with antipyretics and oral fluids; caregiver safety-netting for breathing difficulty and reduced intake."],
            "moderate": ["Admitted to paediatrics: weight-based oseltamivir, monitoring of intake and oxygen saturation."],
            "severe": ["PICU: oseltamivir, oxygen support, watched for febrile convulsion and secondary infection."],
        },
    },

    "asthma_exacerbation": {
        "count": 60, "ages": ("mixed", 0.30),
        "symptoms": {
            "wheeze": 1.00, "dyspnea": 0.90, "dry_cough": 0.80,
            "chest_tightness": 0.70, "fatigue_malaise": 0.30,
            "poor_feeding": 0.20, "irritability": 0.20,
        },
        "core": ["wheeze", "dyspnea"],
        "findings": [
            "Widespread polyphonic expiratory wheeze with prolonged expiratory phase.",
            "Speaking in short sentences; accessory muscle use; widespread wheeze.",
        ],
        "ix": "Peak flow {peakflow}% predicted. Bloods unremarkable; CXR only if consolidation suspected.",
        "assessment": "acute asthma exacerbation - {severity}.",
        "plans": {
            "mild": ["Discharged after back-to-back salbutamol nebs and prednisolone 40 mg for 5 days; inhaler technique checked, action plan updated."],
            "moderate": ["Admitted: oxygen, nebulised salbutamol 30-minutely, oral steroids; ipratropium added."],
            "severe": ["HDU: continuous nebulisers, IV magnesium sulfate, senior and anaesthetic review."],
        },
        "plans_peds": {
            "mild": ["Discharged after spacer-delivered salbutamol 10 puffs and oral prednisolone 1 mg/kg; spacer technique taught to caregivers."],
            "moderate": ["Admitted to paediatrics: oxygen, spacer or nebulised salbutamol, oral steroids; feeding observed."],
            "severe": ["HDU: continuous nebulised salbutamol, IV magnesium, senior paediatric review."],
        },
    },

    "bronchiolitis": {
        "count": 40, "ages": ("peds", 0, 2),
        "symptoms": {
            "dry_cough": 0.95, "wheeze": 0.90, "poor_feeding": 0.85,
            "dyspnea": 0.80, "fever": 0.60, "irritability": 0.50,
            "nausea_vomiting": 0.20,
        },
        "core": ["dry_cough", "wheeze"],
        "findings": [
            "Widespread wheeze and fine crackles, subcostal recession, nasal flaring.",
            "Chest hyperinflated with prolonged expiration; feeding at half usual volumes.",
        ],
        "ix": "Nasopharyngeal swab: RSV positive. CXR: hyperinflation only, no consolidation.",
        "assessment": "RSV bronchiolitis - {severity}.",
        "plans": {
            "mild": ["Discharged with nasal suction and feeding advice; safety-netting for <50% feeds, apnoea or worsening work of breathing."],
            "moderate": ["Admitted to paediatrics: nasal suction, NG feeding, oxygen to keep SpO2 above 92%."],
            "severe": ["HDU: high-flow nasal cannula oxygen, NG feeds, monitoring for apnoea."],
        },
    },

    "pulmonary_embolism": {
        "count": 32, "ages": ("adult", 25, 90),
        "symptoms": {
            "dyspnea": 0.90, "pleuritic_chest_pain": 0.70,
            "unilateral_leg_swelling": 0.40, "palpitations": 0.25,
            "syncope": 0.20, "hemoptysis": 0.15, "fever": 0.20,
        },
        "core": ["dyspnea"],
        "findings": [
            "Tachypnoeic; right calf 3 cm larger than left and tender; chest clear on auscultation.",
            "Oxygen saturation dips on ambulation; no calf signs; tachycardic.",
        ],
        "ix": "D-dimer {ddimer} ng/mL (raised). CTPA: {pe_desc}.",
        "assessment": "pulmonary embolism - {severity}.",
        "plans": {
            "mild": ["Discharged on apixaban 10 mg BD for 7 days then 5 mg BD for 3 months; advice on DVT symptoms."],
            "moderate": ["Admitted: therapeutic apixaban, analgesia, early ambulation."],
            "severe": ["HDU: oxygen, IV fluids, anticoagulation; echo showed right heart strain - thrombolysis discussed."],
        },
    },

    "pericarditis": {
        "count": 24, "ages": ("adult", 22, 80),
        "symptoms": {
            "pleuritic_chest_pain": 0.90, "fever": 0.50, "dyspnea": 0.40,
            "myalgia": 0.30, "palpitations": 0.20, "fatigue_malaise": 0.30,
        },
        "core": ["pleuritic_chest_pain"],
        "findings": [
            "Pericardial friction rub at the left sternal edge; relief leaning forward.",
            "Tachycardic, friction rub audible on inspiration; no murmur.",
        ],
        "ix": "ECG: saddle-shaped ST elevation across precordial leads. CRP {crp} mg/L, troponin mildly raised. Echo: small pericardial effusion, no tamponade.",
        "assessment": "acute pericarditis - {severity}.",
        "plans": {
            "mild": ["Discharged on ibuprofen 400 mg TDS plus colchicine 500 micrograms BD for 3 months; red-flag advice."],
            "moderate": ["Admitted for analgesia, NSAIDs and colchicine; serial ECG and echo."],
            "severe": ["Monitored bed: moderate effusion - repeat echo in 24 h; pericardiocentesis considered."],
        },
    },

    "bacterial_meningitis": {
        "count": 22, "ages": ("mixed", 0.40),
        "symptoms": {
            "fever": 0.95, "headache": 0.85, "neck_stiffness": 0.80,
            "photophobia": 0.60, "nausea_vomiting": 0.50, "confusion": 0.45,
            "rash": 0.30, "myalgia": 0.25,
            "poor_feeding": 0.40, "irritability": 0.60,
        },
        "core": ["fever", "headache", "neck_stiffness"],
        "findings": [
            "Neck stiffness and photophobia on examination{rash_clause}.",
            "Kernig sign positive, meningism{rash_clause}.",
        ],
        "ix": "Bloods: WCC {wcc}, CRP {crp} mg/L, lactate {lactate}. LP: turbid CSF, neutrophils 1,200, protein raised, glucose low.",
        "assessment": "bacterial meningitis - {severity}.",
        "plans": {
            "mild": ["Admitted: IV ceftriaxone 2 g QDS started within the hour plus dexamethasone; LP after CT."],
            "moderate": ["Admitted to the acute medical ward: sepsis six, IV ceftriaxone and dexamethasone; ICU outreach review."],
            "severe": ["ICU: intubation discussed, IV ceftriaxone, dexamethasone and fluid resuscitation; ICP monitoring."],
        },
        "plans_peds": {
            "mild": ["Admitted to paediatrics: IV ceftriaxone 80 mg/kg/day plus dexamethasone; regular observations."],
            "moderate": ["Admitted to paediatric HDU: IV ceftriaxone and dexamethasone; neuro-observations hourly."],
            "severe": ["PICU: IV ceftriaxone, dexamethasone, fluid resuscitation; neuroprotective measures."],
        },
    },

    "nephrotic_syndrome": {
        "count": 18, "ages": ("mixed", 0.70),
        "symptoms": {
            "periorbital_edema": 1.00, "fatigue_malaise": 0.50,
            "abdominal_pain": 0.50, "oliguria": 0.50, "frothy_urine": 0.60,
            "anorexia": 0.40, "diarrhea": 0.15,
        },
        "core": ["periorbital_edema"],
        "findings": [
            "Periorbital and dependent pitting oedema; mild ascites; BP normal for age.",
            "Bilateral pitting leg oedema and facial swelling; abdomen soft with shifting dullness.",
        ],
        "ix": "Urine dip: protein 4+, no blood. Albumin {albumin} g/L, cholesterol raised, renal function normal.",
        "assessment": "nephrotic syndrome, minimal-change disease likely - {severity}.",
        "plans": {
            "mild": ["Day-case management: daily urine dips at home, salt restriction, clinic review in one week."],
            "moderate": ["Admitted: started on prednisolone, salt restriction, monitoring for infection and thrombosis."],
            "severe": ["Admitted: IV albumin for diuresis, prednisolone started, renal biopsy considered."],
        },
    },

    "guillain_barre_syndrome": {
        "count": 15, "ages": ("any", 12, 85),
        "symptoms": {
            "limb_weakness": 1.00, "paresthesia": 0.70, "back_pain": 0.40,
            "fatigue_malaise": 0.50, "dyspnea": 0.30,
        },
        "core": ["limb_weakness"],
        "findings": [
            "Symmetrical distal greater than proximal weakness, power 4/5 in lower limbs, absent ankle reflexes, no sensory level.",
            "Flaccid areflexic weakness ascending from the legs; cranial nerves intact; vital capacity trending down.",
        ],
        "ix": "LP: raised protein with no cells (albuminocytological dissociation). NCS: demyelinating pattern. FVC {fvc} mL, trending.",
        "assessment": "Guillain-Barre syndrome, AIDP variant - {severity}.",
        "plans": {
            "mild": ["Admitted to neurology for observation; twice-daily FVC and bulbar checks; IVIG planned."],
            "moderate": ["Admitted: IVIG 0.4 g/kg/day for 5 days; twice-daily FVC, ECG and swallow assessment."],
            "severe": ["Neuro-ITU: declining vital capacity - ventilatory support discussed with anaesthetics."],
        },
    },

    "mis_c": {
        "count": 10, "ages": ("peds", 3, 15),
        "symptoms": {
            "fever": 1.00, "abdominal_pain": 0.80, "nausea_vomiting": 0.70,
            "rash": 0.60, "conjunctival_injection": 0.50,
            "fatigue_malaise": 0.80, "myalgia": 0.40, "diarrhea": 0.50,
            "dyspnea": 0.30,
        },
        "core": ["fever", "abdominal_pain"],
        "findings": [
            "Toxic but alert; diffuse abdominal tenderness without peritonism; injected conjunctivae; maculopapular rash.",
            "Persistent tachycardia, injected eyes, truncal rash; mild hepatomegaly.",
        ],
        "ix": "CRP {crp} mg/L, ferritin high, troponin mildly raised, BNP raised; COVID serology positive for past infection.",
        "assessment": "paediatric inflammatory multisystem syndrome (MIS-C) - {severity}.",
        "plans": {
            "mild": ["Admitted to paediatrics: IVIG 2 g/kg planned, cardiac echo, fluid restriction."],
            "moderate": ["Admitted: IVIG and methylprednisolone; cardiac monitoring for coronary involvement."],
            "severe": ["PICU: IVIG, methylprednisolone and inotropic support; daily echo."],
        },
    },

    "kawasaki_disease": {
        "count": 3, "ages": ("peds", 1, 7),
        "site_seed": [("B", 1), ("C", 2)],  # the demo's split case: A none, B one, C two
        "symptoms": {
            "fever": 1.00, "rash": 0.95, "conjunctival_injection": 0.90,
            "red_cracked_lips": 0.90, "strawberry_tongue": 0.70,
            "swollen_hands_feet": 0.70, "cervical_lymphadenopathy": 0.60,
            "irritability": 0.70, "poor_feeding": 0.50,
        },
        "core": ["fever"],
        "findings": [
            "Bilateral non-exudative conjunctival injection; cracked red lips with strawberry tongue; polymorphous truncal rash; indurative oedema of the hands and feet; one 2.2 cm tender cervical node.",
        ],
        "ix": "WCC {wcc}, CRP {crp} mg/L, ESR {esr}, platelets {plt} (rising); echocardiogram booked - coronary dimensions normal so far.",
        "assessment": "Kawasaki disease, complete form, day {fever_day} of fever - IVIG needed within 10 days of onset.",
        "plans": {
            "mild": ["Admitted to paediatrics: IVIG 2 g/kg over 12 hours plus aspirin 3 mg/kg; serial echocardiography for coronary aneurysms."],
            "moderate": ["Admitted to paediatrics: IVIG 2 g/kg over 12 hours plus aspirin 3 mg/kg; serial echocardiography for coronary aneurysms."],
            "severe": ["Admitted to paediatric HDU: IVIG 2 g/kg, aspirin, urgent echo and cardiology review for coronary involvement."],
        },
    },
}


def wchoice(pairs):
    items, weights = zip(*pairs)
    return random.choices(items, weights=weights, k=1)[0]


def join_and(items):
    items = [str(i) for i in items]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def symptom_phrase(key):
    if key == "productive_cough":
        return f"productive cough with {random.choice(SPUTUM_COLORS)} sputum"
    return random.choice(SYMPTOM_PHRASES[key])


def age_label(age):
    for lo, hi, label in AGE_BRACKETS:
        if lo <= age <= hi:
            return label
    return "86+"


def height_label(h):
    base = (h // 10) * 10
    return f"{base}-{base + 9}cm"


def weight_label(w):
    base = int(w // 10) * 10
    return f"{base}-{base + 9}kg"


def sample_age(spec):
    kind = spec[0]
    if kind == "mixed":
        if random.random() < spec[1]:
            lo, hi, _ = random.choices(AGE_BRACKETS[:4], weights=PEDS_AGE_WEIGHTS)[0]
        else:
            lo, hi, _ = random.choices(AGE_BRACKETS[4:], weights=ADULT_AGE_WEIGHTS)[0]
        return random.randint(lo, hi)
    lo, hi = spec[1], spec[2]
    if kind == "peds":
        return random.randint(lo, min(hi, 17))
    if kind == "adult":
        return random.randint(max(lo, 18), hi)
    return random.randint(lo, hi)


def sample_body(age, gender):
    if age >= 18:
        if gender == "M":
            height = max(160, min(195, round(random.gauss(176, 7))))
        else:
            height = max(150, min(182, round(random.gauss(163, 7))))
        bmi = max(17.5, min(42.0, random.gauss(27.8, 4.8)))
        weight = round(bmi * (height / 100) ** 2, 1)
        return height, weight, bmi
    if age == 0:
        months = random.randint(3, 11)
        height, weight = 60 + months * 1.7, 6.0 + months * 0.5
    elif age <= 2:
        height, weight = 76 + (age - 1) * 6, 9.5 + (age - 1) * 1.8
    elif age <= 5:
        height, weight = 95 + (age - 3) * 6.5, 14 + (age - 3) * 2.2
    elif age <= 11:
        height, weight = 115 + (age - 6) * 6.8, 20.5 + (age - 6) * 3.4
    else:
        mu_h, mu_bmi = ((172, 20.5) if gender == "M" else (161, 20.0))
        height = random.gauss(mu_h, 7)
        weight = random.gauss(mu_bmi, 3.0) * (height / 100) ** 2
    height = max(55, round(height * random.uniform(0.97, 1.03)))
    weight = round(max(4.5, weight * random.uniform(0.92, 1.08)), 1)
    return height, weight, weight / (height / 100) ** 2


def sample_vitals(age, fever, dyspnea, confusion):
    peds = age < 18
    if fever:
        temp = round(random.uniform(38.5, 40.9) if peds else random.uniform(37.9, 40.2), 1)
    else:
        temp = round(random.uniform(36.1, 37.6), 1)
    if age < 3:
        hr, rr, sbp = random.randint(110, 165), random.randint(30, 44), random.randint(72, 95)
    elif age < 6:
        hr, rr, sbp = random.randint(95, 145), random.randint(22, 32), random.randint(84, 106)
    elif age < 12:
        hr, rr, sbp = random.randint(80, 125), random.randint(18, 26), random.randint(92, 114)
    elif age < 18:
        hr, rr, sbp = random.randint(62, 110), random.randint(14, 22), random.randint(100, 128)
    else:
        hr = round(70 + max(0.0, temp - 37) * 7 + random.randint(-4, 18))
        hr = max(58, min(138, hr))
        rr = random.randint(16, 22)
        sbp = random.randint(82, 89) if random.random() < 0.06 else random.randint(98, 165)
    if dyspnea:
        rr += random.randint(4, 10) if peds else random.randint(3, 9)
    if confusion:
        rr += random.randint(0, 3)
    if not peds and random.random() < 0.08:
        rr = random.randint(30, 36)
    rr = max(14, min(60, rr))
    dbp = round(sbp * 0.6 + random.randint(-4, 6))
    spo2 = random.randint(94, 98)
    if dyspnea:
        spo2 -= random.randint(1, 6)
    if confusion:
        spo2 -= random.randint(0, 3)
    return {"temp": temp, "hr": hr, "rr": rr, "sbp": sbp, "dbp": dbp,
            "spo2": max(84, min(99, spo2))}


def sample_symptoms(disease, cfg, age):
    probs = dict(cfg["symptoms"])
    if disease == "community_acquired_pneumonia":
        probs["confusion"] = (0.28 if age >= 66 else 0.05) if age >= 18 else 0.03
    sx = [k for k, p in probs.items() if random.random() < p]
    sx.extend(c for c in cfg["core"] if c not in sx)
    return [s for s in cfg["core"] if s in sx] + [s for s in sx if s not in cfg["core"]]


def build_case(disease, cfg):
    age = sample_age(cfg["ages"])
    gender = "M" if random.random() < 0.51 else "F"
    race = wchoice(RACES)
    height, weight, bmi = sample_body(age, gender)
    symptoms = sample_symptoms(disease, cfg, age)

    fever = "fever" in symptoms
    dyspnea = "dyspnea" in symptoms
    confusion = "confusion" in symptoms
    vit = sample_vitals(age, fever, dyspnea, confusion)

    labs = {
        "wcc": round(random.uniform(3.5, 6.0) if random.random() < 0.08 else random.uniform(9.5, 19.5), 1),
        "crp": round(random.uniform(35, 330)),
        "urea": round(random.triangular(2.5, 10.0, 4.5) + (random.uniform(0, 3) if age >= 76 else 0), 1),
        "ddimer": random.randint(800, 4500),
        "plt": random.randint(350, 700),
        "esr": random.randint(40, 110),
        "lactate": round(random.uniform(1.0, 4.2), 1),
        "albumin": random.randint(14, 22),
        "fvc": random.randint(1400, 3200),
        "peakflow": random.randint(35, 65),
        "fever_day": random.randint(5, 9),
    }

    peds = age < 18
    rr, spo2, sbp = vit["rr"], vit["spo2"], vit["sbp"]
    # age-adjusted tachypnoea cutoffs (a toddler breathing 38/min is normal)
    if age < 3:
        rr_cut = 50
    elif age < 6:
        rr_cut = 40
    elif age < 12:
        rr_cut = 34
    elif age < 18:
        rr_cut = 28
    else:
        rr_cut = 30
    # age-adjusted hypotension cutoffs (infant SBP 72-95 is normal)
    if age < 3:
        hypot_cut = 70
    elif age < 6:
        hypot_cut = 78
    elif age < 12:
        hypot_cut = 80
    else:
        hypot_cut = 90
    if spo2 <= 89 or sbp < hypot_cut or rr >= rr_cut or (confusion and not peds):
        severity = "severe"
    elif dyspnea or rr >= rr_cut - 6 or (peds and "poor_feeding" in symptoms):
        severity = "moderate"
    else:
        severity = "mild"

    cxr_site = wchoice(CXR_SITES)
    if disease == "community_acquired_pneumonia" and severity == "severe" and random.random() < 0.45:
        cxr_site = "bilateral"
    cxr_desc = "patchy bilateral consolidation" if cxr_site == "bilateral" else f"{cxr_site} consolidation"

    curb_str = ""
    if disease == "community_acquired_pneumonia" and not peds:
        criteria = []
        if confusion:
            criteria.append("confusion")
        if labs["urea"] > 7:
            criteria.append("urea >7 mmol/L")
        if rr >= 30:
            criteria.append("RR >=30")
        if sbp < 90:
            criteria.append("SBP <90")
        if age >= 65:
            criteria.append("age >=65")
        curb_str = f", CURB-65 = {len(criteria)} ({join_and(criteria) if criteria else 'no criteria met'})"

    return {
        "disease": disease, "age": age, "gender": gender, "race": race,
        "height": height, "weight": weight, "bmi": round(bmi, 1),
        "symptoms": symptoms, "peds": peds, "severity": severity,
        "comorbid": [] if peds else [c for c, p in ADULT_COMORBIDS.items() if random.random() < p],
        "cxr_desc": cxr_desc, "curb_str": curb_str, **vit, **labs,
        "pe_desc": random.choice([
            "segmental pulmonary embolism in the right lower lobe artery",
            "subsegmental clot in the left basal segment",
            "large lobar embolus with right heart strain",
        ]),
    }


def build_text(c, cfg):
    gender = c["gender"]
    person = ("man" if gender == "M" else "woman") if not c["peds"] else ("boy" if gender == "M" else "girl")
    age_str = f"{c['age']}-year-old" if c["age"] >= 1 else f"{random.randint(3, 11)}-month-old"

    phrases = {k: symptom_phrase(k) for k in c["symptoms"] if k != "confusion"}
    story_keys = [k for k in c["symptoms"] if k != "confusion"]
    main = join_and(phrases[k] for k in story_keys[:3])
    if c["peds"]:
        opener = random.choice(PEDS_OPENERS).format(
            age_str=age_str, person=person, carer=random.choice(["mother", "father", "parents"]),
            dur=random.randint(2, 7), main=main)
    else:
        opener = random.choice(ADULT_OPENERS).format(
            age=c["age"], person=person, person_c=person.capitalize(),
            dur=random.randint(2, 10), main=main)
    if len(story_keys) > 3:
        opener += f" Associated symptoms: {join_and(phrases[k] for k in story_keys[3:])}."
    if "confusion" in c["symptoms"]:
        opener += " " + random.choice(CONFUSION_HPI)

    if c["peds"]:
        pmh = "Background: " + random.choice(PEDS_PMH)
    else:
        pmh = "PMH: " + (join_and(c["comorbid"]) + "." if c["comorbid"] else "nil of note.")
        r = random.random()
        if r < 0.24:
            pmh += f" Current smoker ({random.randint(5, 25)} cigarettes/day)."
        elif r < 0.44:
            pmh += " Ex-smoker."
        else:
            pmh += " Never smoked."

    finding = random.choice(cfg["findings"]).format(
        zone=CXR_ZONES.get(next((s for s, _ in CXR_SITES
                                 if c["cxr_desc"].startswith(s) and "bilateral" not in c["cxr_desc"]),
                                 "bilateral"), "both bases"),
        rash_clause="; non-blanching petechial rash over the trunk" if "rash" in c["symptoms"] else "; no rash",
    )
    oe = (f"O/E: T {c['temp']} degC, HR {c['hr']} bpm, RR {c['rr']}/min, "
          f"BP {c['sbp']}/{c['dbp']} mmHg, SpO2 {c['spo2']}% on room air. {finding}"
          + (f" BMI {c['bmi']:.1f}." if not c["peds"] and c["bmi"] >= 30 else ""))

    ix = cfg["ix"].format(**c)
    assessment = "Assessment: " + cfg["assessment"].format(**c)
    plans = cfg.get("plans_peds") if c["peds"] and cfg.get("plans_peds") else cfg["plans"]
    plan = "Plan: " + random.choice(plans[c["severity"]])

    return "\n\n".join([opener, pmh, oe, ix, assessment, plan])


def build_record(disease, cfg, used_ids, site):
    while True:
        rid = "".join(random.choices("0123456789ABCDEF", k=8))
        if rid not in used_ids:
            used_ids.add(rid)
            break
    c = build_case(disease, cfg)
    text = build_text(c, cfg)
    record = {
        "record_id": rid,
        "disease": disease,
        "symptoms": c["symptoms"],
        "gender": c["gender"],
        "age_bracket": age_label(c["age"]),
        "race": c["race"],
        "height_bracket": height_label(c["height"]),
        "weight_bracket": weight_label(c["weight"]),
        "text": text,
    }
    return record, c


def validate(records, cases):
    ids = [r["record_id"] for r in records]
    assert len(set(ids)) == len(ids), "duplicate record_id"
    for r in records:
        assert set(r) == {"record_id", "disease", "symptoms", "gender", "age_bracket",
                          "race", "height_bracket", "weight_bracket", "text", "site"}
        assert r["disease"] in DISEASES
        assert r["symptoms"] and set(r["symptoms"]) <= set(SYMPTOM_PHRASES), f"bad symptom {r['record_id']}"
        assert r["gender"] in ("M", "F")
        assert r["age_bracket"] in {b[2] for b in AGE_BRACKETS}
        assert r["race"] in {x[0] for x in RACES}
        assert r["site"] in SITES
    for r in records:
        if r["disease"] == "community_acquired_pneumonia":
            assert "pneumonia" in r["text"].lower()
        if r["age_bracket"] in ("0-2", "3-5", "6-11", "12-17"):
            assert "CURB" not in r["text"], f"CURB-65 in a pediatric note: {r['record_id']}"
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "data")
    args = ap.parse_args()

    random.seed(args.seed)
    used_ids = set()
    records, cases = [], []

    for disease, cfg in DISEASES.items():
        site_seed = cfg.get("site_seed")
        for i in range(cfg["count"]):
            if site_seed:
                site, assigned = site_seed[-1][0], 0
                for s, cnt in site_seed:
                    if i < assigned + cnt:
                        site = s
                        break
                    assigned += cnt
            else:
                site = random.choice(SITES)
            rec, case = build_record(disease, cfg, used_ids, site)
            records.append({**rec, "site": site})
            cases.append(case)

    validate(records, cases)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sites").mkdir(exist_ok=True)
    n = len(records)

    with (args.out / f"patients_{n}.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (args.out / f"patients_{n}.json").open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    with (args.out / f"patients_{n}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "disease", "gender", "age_bracket", "race",
                    "height_bracket", "weight_bracket", "symptoms", "site", "text"])
        for r in records:
            w.writerow([r["record_id"], r["disease"], r["gender"], r["age_bracket"], r["race"],
                        r["height_bracket"], r["weight_bracket"], "; ".join(r["symptoms"]),
                        r["site"], r["text"]])
    for s in SITES:
        with (args.out / "sites" / f"site_{s.lower()}.jsonl").open("w", encoding="utf-8") as f:
            for r in records:
                if r["site"] == s:
                    f.write(json.dumps({k: v for k, v in r.items() if k != "site"},
                                       ensure_ascii=False) + "\n")

    # ------------------------------------------------ stats
    peds = [r for r in records if r["age_bracket"] in ("0-2", "3-5", "6-11", "12-17")]
    dc = Counter(r["disease"] for r in records)
    sc = Counter(r["site"] for r in records)
    ab = Counter(r["age_bracket"] for r in records)
    kawa = [(r["record_id"], r["site"]) for r in records if r["disease"] == "kawasaki_disease"]
    sev = Counter(c["severity"] for c in cases)
    lens = [len(r["text"]) for r in records]
    print(f"records: {n} | unique ids: {len({r['record_id'] for r in records})}")
    print(f"pediatric (<18): {len(peds)} ({len(peds)/n:.0%}) | adult: {n - len(peds)}")
    print("age_bracket: " + ", ".join(f"{k}={v}" for k, v in sorted(ab.items())))
    print("diseases: " + ", ".join(f"{k}={v}" for k, v in dc.most_common()))
    print("sites: " + ", ".join(f"{k}={v}" for k, v in sorted(sc.items())))
    print(f"kawasaki split-case: {kawa}")
    print(f"severity: mild={sev['mild']} moderate={sev['moderate']} severe={sev['severe']}")
    print(f"note chars: min={min(lens)} mean={sum(lens)//n} max={max(lens)}")
    print("validation: OK")


if __name__ == "__main__":
    main()
