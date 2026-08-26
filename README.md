# Synthetic multi-disease patient dataset — hackathon-sammz

500 synthetic patient records, **11 diseases, all ages (0 to 86+, 32% paediatric)**,
split across **three hospital sites**, built for the Rare Disease Consult Network
demo ([hackathon-sammz](https://github.com/mfarzi/hackathon-sammz)).

All data is synthetic (seeded random generation) — **no real patient data** —
and must not be used for clinical purposes.

## Files

| File | Description |
|---|---|
| `consult_console.html` | **The demo UI** — self-contained; double-click to run. Pick a case, run the consult, watch the network answer. |
| `dataset_preview.html` | Searchable/filterable table of all 500 records |
| `generate_dataset.py` | Seeded generator (stdlib only, Python 3.8+) |
| `console_template.html` | Console source; `__SITE_DATA__` gets injected from the site files |
| `data/patients_500.jsonl` | All 500 records + `site` field, one per line |
| `data/patients_500.json` / `.csv` | Same records as JSON array / spreadsheet |
| `data/sites/site_{a,b,c}.jsonl` | Per-site files — PLAN.md schema exactly, no extra fields |

## Record schema

```json
{
  "record_id": "7F3A2C91",
  "disease": "kawasaki_disease",
  "symptoms": ["fever", "rash", "conjunctival_injection"],
  "gender": "F",
  "age_bracket": "3-5",
  "race": "White",
  "height_bracket": "80-89cm",
  "weight_bracket": "10-19kg",
  "text": "<free-text ED clerking note>"
}
```

`record_id` and `text` never leave the site. Everything else is bracketed or
categorical. Clinical notes are internally consistent: symptoms, vitals,
age-appropriate norms (infant HR/RR/BP, weight-based dosing) and severity
(CURB-65 for adult CAP only — never for children) all match.

## Diseases (counts)

community_acquired_pneumonia 210 · influenza 66 · asthma_exacerbation 60 ·
bronchiolitis 40 (infants) · pulmonary_embolism 32 · pericarditis 24 ·
bacterial_meningitis 22 · nephrotic_syndrome 18 · guillain_barre_syndrome 15 ·
mis_c 10 (paediatric) · **kawasaki_disease 3 — the seeded split case**

## Demo narrative (seeded)

`kawasaki_disease` has exactly 3 cases in the whole network:
**site A: 0 · site B: 1 · site C: 2** — no single site can answer, the network
can. The console's retrieval (Jaccard symptom overlap + demographic bonus,
threshold 0.40, top-3-mean ranking with count as provenance) finds them and
site A correctly answers NO DATA.

## Regenerate

```bash
python3 generate_dataset.py            # reproducible, seed 20260826
python3 generate_dataset.py --seed 7   # different dataset
```
