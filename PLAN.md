# Rare Disease Consult Network

A clinician describes a patient nobody can place. Every hospital in the network
checks its own records, reasons over its own notes, and answers — without a
single patient record leaving the building.

**Track 1 — Flower Agent Harness.** Collaborative Agent Hackathon, Cambridge,
26 August 2026. Built on the adversarial review panel in this repo.

## The problem is that the evidence is scattered

A rare disease is rare at any one hospital and not rare across fifty. The
consultant seeing an unusual presentation has one or two comparable cases in
living memory, and no way to reach the three cases sitting in a hospital two
hundred miles away. The data that would settle the question exists — it is just
distributed, and it cannot be centralised, because it is patient records.

That makes this the rare case where federation is not architectural decoration.
The value comes from pooling the long tail, and the long tail is exactly what no
single site can see.

> No single site has enough cases to make the call. The network does.

## How a consult runs

Six stages, two round-trips across the network, one adversarial review before
anything reaches the clinician.

**1. The clinician describes the case in plain language.** *(hub agent)* One
model call turns free text into a structured query: symptom set, age bracket,
sex, and any other bracketed demographics. No identifiers are constructed and
none are needed.

**2. The query fans out to every site at once.** *(hub → all sites, parallel)*
The hub sends the same structured query to every hospital node simultaneously
and waits for replies. Sites that have never seen anything comparable answer
with no data, which is itself a useful result.

**3. Each site agent reads its own clinical notes.** *(site agent, inside the
hospital)* The site retrieves candidate records by symptom overlap, then its
agent reads the full free-text notes locally and writes an abstraction: what the
matching cases had in common, how the illness progressed, what was notably
absent. The notes themselves never move.

**4. The hub asks a follow-up question it could not have asked at the start.**
*(hub → selected sites)* Having read every site's answer, the hub works out what
would actually discriminate between the leading candidates and asks specific
sites a specific question. Those sites answer from their own records. This is
the hop that makes it a consultation rather than a search.

**5. Five blind specialists attack the candidate diagnoses.** *(review panel, at
the hub)* The existing adversarial review panel is retargeted from code defects
onto diagnoses. Five reviewers with disjoint mandates assess independently;
every surviving candidate is then attacked by three reviewers who did not raise
it.

**6. The report shows what survived and what was killed.** *(master →
clinician)* Survivors carry their dissent. Rejected candidates are shown rather
than hidden. Anything with too few verdicts is labelled unverified rather than
counted as agreement.

## What crosses the hospital boundary

```
 ┌──────────────┐                ┌ hospital site ──────────── ×N, in parallel ┐
 │  hub agent   │                │                                            │
 │              │─ symptom set ─►│  patient records ──reads──► site agent     │
 │  ServerApp   │  + brackets    │  notes, symptoms            ClientApp      │
 │  + review    │                │                                            │
 │    panel     │◄─ disease ─────│                                            │
 │              │   score, count │  never leaves this box:                    │
 │              │   + abstraction│  record_id · free text · anything          │
 │              │                │  identifying                               │
 │              │─ follow-up ───►│                                            │
 └──────────────┘  "renal        │                                            │
                    involvement?"└────────────────────────────────────────────┘
```

The site agent sits *on* the boundary rather than behind it. Raw notes are read
where they live; what crosses the wire is a judgement the agent wrote, not a
record it copied.

## Three things that make this more than federated search

**The agent is the privacy boundary.** The obvious way to protect the free-text
notes is to refuse to send them. That also throws away the clinical richness —
the temporal course, the response to treatment, the finding that was notably
absent. Putting a reading agent inside the hospital keeps both: the note never
moves, and its content still reaches the network as an abstraction the site
authored.

**The panel proves it can still say no.** A review panel that never rejects
anything is a rubber stamp, and "it survived review" then means nothing. So a
deliberately false diagnosis rides through the refutation round disguised as a
real candidate. If the panel kills it, the run's verdicts carry weight. If it
survives, the report leads with a calibration failure and says the results
should not be trusted.

**Common diseases don't win on volume.** The corpus is wildly uneven — hundreds
of cases for some diseases, one or two for many. Score by match count and the
well-published diseases swamp the genuinely rare ones, which is the opposite of
the point. Ranking uses the mean of the top three similarity scores across the
whole network, with no penalty for having fewer than three. Case count travels
as provenance and never touches the score.

## How the panel decides

```
  candidates from ──┐
  the network       │
                    ├─► 3 blind refuters ──┬─► survivor    withstood attack,
  1 planted         │   each, drawn from   │               dissent attached
  false diagnosis ──┘   lenses that did    │
  (indistinguishable    not raise it       ├─► killed      majority refuted,
   to the refuters)                        │               shown not hidden
                        "refute,           │
                         don't discuss"    └─► unverified  too few votes, never
                                                           read as agreement

  calibration ─ planted diagnosis killed → the other verdicts mean something
                it survived              → the report opens by saying this run
                                           should not be trusted
```

The burden of proof sits with the finding: refuters default to rejecting when
uncertain, so a diagnosis survives only by withstanding a genuine attempt to
break it.

## What runs where

Agents do the judgement. The one number used for ranking stays deterministic,
because scores from different sites have to be comparable or the ranking
measures scoring noise instead of similarity.

| Component | Runs | Does | Kind |
| --- | --- | --- | --- |
| Query parser | Hub | Clinician's free text → structured symptom set and demographics | agent |
| Record retrieval | Each site | Symptom-set overlap against local records; identical code everywhere | deterministic |
| Site agent | Each site | Reads matched notes locally, writes the abstraction, flags what argues against | agent |
| Follow-up | Hub → sites | Decides the discriminating question; sites answer from their own records | agent |
| Aggregation | Hub | Top-3-mean ranking across the network; count kept as provenance | deterministic |
| Review panel | Hub | Five blind lenses, refutation round, calibration probe, final report | agent |

This mirrors a split the review panel already makes deliberately: its master
ranks candidates mechanically and decides nothing about truth. Retrieval decides
what gets discussed; agents decide what it means.

## The demo

The story the run has to tell is a diagnosis **no single site could have reached
alone**. One site holds a single comparable case. Another holds two. Neither is
enough on its own, and the network gets there. Everything else in the pitch is
machinery serving that moment.

Three beats worth showing on screen:

- A site answering **no data** — the negative result is part of the value, not a
  gap in the demo.
- The **follow-up question** being composed and sent, because that is the moment
  it stops looking like search.
- The **calibration line** in the report, confirming the panel rejected the
  planted diagnosis on this run.

## Before anything goes on a slide

**One load-bearing assumption is still unverified.** The panel reaches its model
through Flower runtime environment variables. We have confirmed that `AgentApp`
cannot address hospital nodes at all — fan-out requires `ServerApp` and `Grid`,
and `AgentSession` exposes only `connectors`, `events`, and `responses` — so the
whole system has to run as a ServerApp. What we have *not* confirmed is that
model calls work inside a ServerApp process on SuperGrid. A twenty-minute spike
settles it. Until it comes back, don't put a claim on a slide that depends on
the two halves running in one place.

Also worth knowing:

- **Timing is tight.** Roughly 30 model calls across two network round-trips,
  inside SuperGrid's five-minute task timeout. If the clock bites, cut
  candidates and refuters before cutting the follow-up hop — the panel degrades
  gracefully, and the follow-up is what makes this collaborative.
- **Local simulation is the safer demo.** Three nodes in simulation removes
  network flakiness from the live run without weakening the story.
- **The dataset has to be seeded for the narrative.** The split case described
  above needs to exist on purpose rather than by luck.

## Record format

Assumed already present at each site:

```json
{
  "record_id": "7F3A2C91",
  "disease": "some_rare_disease",
  "symptoms": ["dyspnea", "productive_cough", "fever", "rigors", "confusion"],
  "gender": "M",
  "age_bracket": "51-65",
  "race": "White",
  "height_bracket": "170-179cm",
  "weight_bracket": "80-89kg",
  "text": "<free-text clinical note>"
}
```

`record_id` and `text` never leave the site. Everything else is already
bracketed or categorical.
