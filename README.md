# Rare Disease Consult Network

A Flower federation where a clinician consults every hospital at once about a
patient nobody can place — and an adversarial panel attacks the answers before
they reach anyone.

**Track 1 — SuperGrid.** Collaborative Agent Hackathon, Cambridge,
26 August 2026.

## The idea

A rare disease is rare at any one hospital and not rare across fifty. The
consultant seeing an unusual presentation has one or two comparable cases in
living memory and no way to reach the three sitting in a hospital two hundred
miles away. The data that would settle the question exists; it is just
distributed, and it cannot be centralised, because it is patient records.

So the query travels instead of the data.

```
 ┌──────────────┐                ┌ hospital site ──────────── ×N, in parallel ┐
 │  hub agent   │                │                                            │
 │              │─ symptom set ─►│  patient records ──reads──► site agent     │
 │  ServerApp   │  + brackets    │  notes, symptoms            ClientApp      │
 │  + panel     │                │                                            │
 │              │◄─ disease ─────│                                            │
 │              │   score, count │  never leaves this box:                    │
 │              │   + abstraction│  record_id · free text · anything          │
 │              │                │  identifying                               │
 │              │─ follow-up ───►│                                            │
 └──────────────┘  "K-F rings?"  └────────────────────────────────────────────┘
```

Six stages: the clinician's description is parsed into a structured query; it
fans out to every hospital at once; each site searches its own records and its
own agent reads the matching notes locally; the hub asks one targeted follow-up
it could not have known to ask at the start; the panel attacks what came back;
the master reports what survived.

## The site agent is the privacy boundary

The obvious way to protect the free-text notes is to refuse to send them. That
also throws away the clinical richness — the temporal course, the response to
treatment, the finding that was notably absent — which is most of what
distinguishes a rare disease from a common one.

Putting a reading agent inside the hospital keeps both. The note never moves,
and its content still reaches the network as an abstraction the site wrote:
*"all four of our cases showed slit-lamp-confirmed Kayser–Fleischer rings; none
had fever at onset."* What crosses the wire is a judgement, not a record.

`_strip_for_wire` is an allowlist rather than a blocklist, so a field added to
the record format later cannot leak by being forgotten.

## Case count is provenance, not strength

The corpus is wildly uneven — 3,528 cases of community-acquired pneumonia, 8 of
addisonian crisis. Any score that scales with the number of matching patients
hands the top of the list to whatever is best published, which is the exact
opposite of the point.

So ranking uses the **mean of the network's best three similarity scores**,
taking fewer if fewer exist and never padding with zeros. One case at 0.80 beats
a hundred cases topping out at 0.80 / 0.79 / 0.78. Case count travels as
provenance and never touches the score; it is labelled as such in every prompt,
so a lens cannot quietly read volume as evidence.

Similarity itself is deliberately dumb — Jaccard overlap of symptom sets,
computed by identical code at every site. It has to be: sites are separate
processes in separate institutions, and if each scored with its own model call,
a 0.85 from one and a 0.85 from another would not be the same claim. Retrieval
decides what gets discussed. The agents decide what it means.

## The panel never converges by discussion

Five lens agents assess the network's candidates independently and in parallel,
each with a disjoint mandate — symptom fit, demographic plausibility, common
explanations, evidence quality, contradicting evidence. None can see the others.

Then every candidate is attacked by three lenses, each told to **refute rather
than discuss**, each defaulting to *refuted* when uncertain, each still blind to
the other verdicts. The burden of proof sits with the candidate. A candidate
dies on a majority of refutations.

Showing round-1 results to all five and asking them to agree would correlate
their judgements and turn consensus into a measure of contagion rather than
correctness. That matters more here than in code review, because anchoring on
the first plausible diagnosis is the classic way a differential goes wrong.

Agreement must not reduce scrutiny either. Refuters are drawn first from lenses
with no stake in a candidate, but the count is always filled — topping up from
the lenses that raised it when too few disinterested ones remain. Without that,
a candidate raised by four of five lenses drew a single verdict, fell below
`min-votes`, and was reported as *unverified*: the best-corroborated finding
getting the least scrutiny, which inverts the whole point of running round 1
blind.

## The calibration probe

A panel that never rejects anything is indistinguishable from a rubber stamp,
and "it survived refutation" then carries no information.

So one **known-false candidate** rides through round 2 alongside the real ones,
indistinguishable to the refuters. It asserts multi-site support for a disease no
site reported at all — checkable against the evidence, and wrong. If the refuters
kill it, the run's verdicts mean something. If it survives, the report leads with
a calibration failure and says plainly that the other verdicts should not be
trusted.

The system measures its own reliability on every run, and reports the answer
whether or not it is flattering.

## Safety and oversight

Not retrofitted — it is what the architecture is for.

- **Nothing identifying leaves a hospital.** Record identifiers and free-text
  notes are read locally and dropped; only an allowlist of fields is ever copied
  onto the wire.
- **Every verdict is attributable.** Which lens raised a candidate, which
  attacked it, how each voted, and their reasoning all reach the report.
- **Dissent survives to the output.** A 1-of-3 split is never presented as
  unanimous.
- **Thin evidence is labelled, not counted.** A candidate drawing fewer than
  `min-votes` verdicts is reported as *unverified* rather than as a survivor. A
  refuter that crashed cast no vote and is never read as agreement.
- **No silent truncation.** Diseases trimmed by the per-site cap, candidates
  dropped by the candidate cap, lenses that failed, and sites that never answered
  are all stated in the report. A site that did not reply is never counted as a
  site that found nothing.
- **The vocabulary is closed.** An unconstrained parse produces plausible
  synonyms that match no record, and an empty consult looks identical to one that
  genuinely found nothing. Symptoms are mapped onto a shared vocabulary and
  anything unrecognised is reported, not dropped in silence.
- **It advises, it does not diagnose.** Every prompt says so, and the report
  describes case counts as leads to investigate rather than proof.
- **The system flags its own unreliability** via the calibration probe.

## Running it

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
