# Synthetic multi-disease patient dataset — hackathon-sammz

500 synthetic patient records, **11 diseases, all ages (0 to 86+, 32% paediatric)**,
split across **three hospital sites**, built for the Rare Disease Consult Network
demo ([hackathon-sammz](https://github.com/mfarzi/hackathon-sammz)).

All data is synthetic (seeded random generation) — **no real patient data** —
and must not be used for clinical purposes.

## Collaboration layout

| Path | Owner | Contents |
| --- | --- | --- |
| `review_panel/` | backend / agent | Flower AgentApp orchestration |
| `fixtures/` | backend | Demo code under review (`buggy_cart`) |
| `tests/` | backend | Offline panel tests |
| `pyproject.toml`, `uv.lock` | backend | Python deps |
| `frontend/` | frontend | Next.js design system + UI |

Prefer working in different top-level folders to avoid merge conflicts.

## Frontend (design system)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 for the token specimen. Product screens come next.

## The idea
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
review_panel/agent_app.py   orchestration, dedupe, vote accounting, report
review_panel/lenses.py      the five mandates and both rounds' prompts
review_panel/model.py       runtime-bound OpenAI client, JSON schemas
fixtures/buggy_cart/        demo target: real defects and unlabelled traps
tests/test_panel.py         offline checks
frontend/                   Next.js design system (App Router)
consult/server_app.py    hub: parse, fan-out, follow-up hop, panel, report
consult/client_app.py    hospital site: search, local note reading, follow-up
consult/panel.py         five blind lenses, refutation, calibration probe
consult/lenses.py        the five diagnostic mandates and both rounds' prompts
consult/scoring.py       similarity and the top-3-mean network ranking
consult/records.py       per-site retrieval; notes stay local
consult/vocabulary.py    the closed symptom vocabulary and the parse constraint
consult/protocol.py      what travels between hub and sites
review_panel/            the code-review panel this was retargeted from
```

## Built on

Flower 1.35.0, running as a `ServerApp` fanning out over `Grid.send_and_receive`
to a `ClientApp` at each hospital. Round-1 and round-2 model calls fan out across
threads, so the panel is genuinely concurrent rather than a loop of sequential
calls.

Local simulation needs Python ≤ 3.13 and `ray`, which is why `ray` is named
explicitly in the dependencies — Flower's runtime env installs exactly what the
app declares.

One thing still untested: a ServerApp running locally gets no model credentials
from the Flower runtime (`FLWR_RUNTIME_BASE_URL` is unset), so runs here go
through the OpenAI API directly. Whether SuperGrid supplies them to a ServerApp
has not been confirmed.
