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

<p align="center">
  <img src="https://github.com/mfarzi/hackathon-sammz/blob/main/docs/dataflow.svg" alt="The clinician's query fans out to every hospital; each site reads its own notes locally and returns an abstraction; record identifiers and free text never cross the boundary." width="100%">
</p>

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

Five simulated hospitals on one machine:

```bash
export PATH="$PWD/.venv/bin:$PATH"   # flwr launches flower-superlink from PATH

# once: the simulation defaults to 2 SuperNodes since flwr 1.32, and this
# project needs one per hospital
flwr federation simulation-config @none/default local --num-supernodes 5

CASE='Woman in her twenties, months of worsening tremor and slurred speech, with a marked change in mood and behaviour noted by family. Jaundiced on examination. Persistently tired. No fever.'

flwr run . local --stream --run-config \
  "panel.model='gpt-5.6-sol' consult.case='$CASE'"
```

Three things that must be right:

- **Five SuperNodes, or five hospitals become two.** The federation config moved
  out of `pyproject.toml` into the Flower configuration file, so the old
  `options.num-supernodes = 5` no longer applies. Set it once with the command
  above; otherwise the consult silently runs on two sites.
- `panel.model` needs the bare model id when running against the OpenAI API
  directly; the `openai/` prefix in the default is a Flower runtime ref.
- `.venv/bin` must be on `PATH`, or `flwr` cannot launch `flower-superlink`.

Credentials come from `OPENAI_API_KEY`, found either in the environment or in a
`.env` file at or above the working directory. Flower runs the ServerApp and each
ClientApp as separate processes and a SuperLink started earlier will not inherit
a later `export`, so the app looks for the file itself rather than depending on
launch order. Where no runtime credentials exist at all, `panel.api-key` can
carry a key in the run config — it is visible in run metadata wherever the
SuperLink is hosted, so rotate anything sent that way.

### Rehearsing without spending a token

```bash
flwr run . local --stream --run-config \
  "consult.dry-run=true consult.symptoms='jaundice,tremor,dysarthria,mood_change,fatigue'"
```

Fan-out, per-site search, and ranking, with no agents and no panel. Proves the
federation works and takes about 21 seconds.

### Configuration

| Key | Default | Meaning |
| --- | --- | --- |
| `consult.case` | *(built-in example)* | The clinician's description, in plain language |
| `consult.data-dir` | `consult/sample_data` | Where each node reads `<site-name>.jsonl` |
| `consult.symptoms` | `""` | Skip the parse with an explicit comma-separated list |
| `consult.followup` | `true` | Ask one targeted follow-up after round 1 |
| `consult.dry-run` | `false` | Retrieval and ranking only; no model calls |
| `panel.model` | `openai/gpt-5.6-sol` | Model ref for every agent |
| `panel.api-key` | `""` | Model key for deployments where the runtime supplies none |
| `panel.max-candidates` | `5` | Candidates carried into round 2 |
| `panel.refuters-per-finding` | `3` | Independent attackers per candidate |
| `panel.min-votes` | `2` | Verdicts needed before survival counts |
| `panel.canary` | `true` | Run the calibration probe |

Roughly 30 model calls across two network round-trips.

### On SuperGrid

The venue network blocks 9092/9093, so SuperNodes cannot reach the Fleet API and
the deployment federation is unreachable from here. Runs go to SuperGrid's
simulation federation over 443 instead. That is why `consult/sample_data`
exists: the full corpus is 33 MB with an 11.9 MB largest file, and both the Hub
and the FAB are far smaller than that. Sampling keeps every rare disease whole
and thins the common ones, so the long tail the ranking rule exists for survives
the shrink. `docker/` holds a container per hospital.

## A worked run

A woman in her twenties with months of tremor, slurred speech, behavioural
change, and jaundice. Five hospitals, 1,689 sampled records, retrieval and
ranking only:

```
wilson_disease                        0.500 |  10 cases | all five sites
hypothyroidism                        0.200 |   6 cases | two sites
thrombotic_thrombocytopenic_purpura   0.200 |   1 case  | one site
iron_deficiency_anaemia               0.178 |   8 cases | two sites
```

Two things to read off it. Wilson disease sits top at 0.500, contributed by all
five hospitals at two cases each — no single site holds enough to call it, and
together they do. And one case at 0.200 outranks eight at 0.178: case count
travels as provenance and never touches the score.

On the full 75,001-record corpus the same case put Wilson at 0.405 on 7 cases
above iron-deficiency anaemia on 178, a starker inversion. Sampling thins the
common diseases, so the gap narrows while the ordering rule holds.

## Tests

```bash
PYTHONPATH=. python tests/test_consult.py   # 64 checks
PYTHONPATH=. python tests/test_panel.py     # 46 checks, the original panel
```

Offline, no model calls. They cover the rules the claims rest on: that count
never drives ranking, that nothing identifying reaches the wire, that a candidate
is never silently promoted to survivor, and that agreement never shrinks the
refuter pool.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 for the token specimen.

## The synthetic 500-record dataset

A separate seeded corpus — 500 records, 11 diseases, three sites — built for the
console UI. Distinct from `consult/sample_data`, which is what the federation
reads.

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

## Layout

```
consult/server_app.py     hub: parse, fan-out, follow-up hop, panel, report
consult/client_app.py     hospital site: search, local note reading, follow-up
consult/panel.py          five blind lenses, refutation, calibration probe
consult/lenses.py         the five diagnostic mandates and both rounds' prompts
consult/scoring.py        similarity and the top-3-mean network ranking
consult/records.py        per-site retrieval; notes stay local
consult/vocabulary.py     the closed symptom vocabulary and the parse constraint
consult/protocol.py       what travels between hub and sites
consult/sample_data/      the sampled corpus the federation reads
data/                     the full 75,001-record corpus
docker/                   a container per hospital
docs/dataflow.svg         the data flow diagram above
frontend/                 Next.js design system (App Router)
review_panel/             the code-review panel this was retargeted from
tests/                    offline checks for both
```

## Built on

Flower 1.35.0, running as a `ServerApp` fanning out over `Grid.send_and_receive`
to a `ClientApp` at each hospital. Round-1 and round-2 model calls fan out across
threads, so the panel is genuinely concurrent rather than a loop of sequential
calls.

Local simulation needs Python ≤ 3.13 and `ray`, which is why `ray` is named
explicitly in the dependencies — Flower's runtime env installs exactly what the
app declares.

A ServerApp gets no model credentials from the Flower runtime, so runs go
through the OpenAI API directly — from the environment, a `.env` file, or
`panel.api-key`. The deployment federation is unreachable from the venue
(9092/9093 blocked), so runs use SuperGrid's simulation federation over 443.
