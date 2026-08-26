# Adversarial Review Panel

A Flower AgentApp that reviews code with five blind specialists, then attacks
its own findings before reporting them.

**Track 1 — Flower Agent Harness.** Collaborative Agent Hackathon, Cambridge,
26 August 2026.

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

Most multi-agent review systems fan out, collect opinions, and let the agents
discuss until they agree. That is the wrong shape. Five *independent* judgements
are valuable precisely because their errors are uncorrelated; the moment you
show round-1 results to every agent and ask them to converge, you get anchoring.
The agents settle on whatever was stated first or loudest, and the consensus
that emerges measures **contagion, not correctness**. Worse, it fails hardest in
exactly the cases you care about: a unanimous verdict reached by discussion looks
more trustworthy than a split verdict reached independently, even when the split
one was right.

So this panel never converges by discussion. It runs two rounds, both blind.

```
             ┌─ correctness ─┐
             ├─ security ────┤
  code ──────┼─ performance ─┼──► master ──► candidates
             ├─ robustness ──┤   (dedupe,      │
             └─ contracts ───┘    rank)        │
             round 1: blind, parallel          │
                                               ▼
             ┌─ 3 lenses that did NOT raise it ─┐
             │  each asked to REFUTE, not discuss│
             └───────────────┬───────────────────┘
             round 2: blind, parallel
                             ▼
        survivors + dissent + what got killed + calibration
```

**Round 1.** Five lens agents review the target in parallel. Each has a narrow,
disjoint mandate, because five agents given the same prompt only sample variance
whereas five given different mandates catch failure modes that redundancy cannot.
None can see the others.

**Master.** Deduplicates and ranks. It decides nothing about truth.

**Round 2.** Every candidate is attacked by three lenses that did not raise it,
each told to refute rather than discuss, each defaulting to *refuted* when
uncertain, and each still blind to the other verdicts. The burden of proof sits
with the finding. A finding dies on a majority of refutations.

**Report.** Survivors carry their dissent. Killed findings are shown, not hidden
— seeing what did not survive is what makes the survivors worth trusting.

## The calibration probe

A panel that never rejects anything is indistinguishable from a rubber stamp,
and "it survived refutation" then carries no information.

So one **known-false finding** rides through round 2 alongside the real
candidates, indistinguishable from them to the refuters. Its claim is checkable
against the code and wrong. If the refuters kill it, the run's verdicts mean
something. If it survives, the report leads with a calibration failure and says
plainly that the other verdicts should not be trusted.

The system measures its own reliability on every run, and reports the answer
whether or not it is flattering.

## Safety and oversight

Not retrofitted — it is what the architecture is for.

- **Nothing is mutated.** The panel reads code and reports. It cannot edit,
  commit, or execute the code under review.
- **Every verdict is attributable.** Which lens raised a finding, which lenses
  attacked it, how each voted, and their stated reasoning all reach the report.
- **Dissent survives to the output.** A 1-of-3 split is never presented as
  unanimous.
- **Thin evidence is labelled, not counted.** A finding that drew fewer than
  `min-votes` verdicts is reported as *unverified* rather than as a survivor. A
  refuter that crashed cast no vote and is never silently read as agreement.
- **No silent truncation.** Candidates dropped by a cap, reviewers that failed,
  and source that was too long to review are all stated in the report. A capped
  panel that quietly reports "all clear" would be lying.
- **The system flags its own unreliability** via the calibration probe.

## Running it

```bash
flwr run . supergrid --stream
```

Review something else:

```bash
flwr run . supergrid --stream \
  --run-config 'panel.target="path/to/code" agent.input="focus on the auth path"'
```

`panel.target` is resolved inside the app directory and must stay there, so
whatever you want reviewed needs to be listed in `fab-include` to ship with the
app.

### Configuration

| Key | Default | Meaning |
| --- | --- | --- |
| `panel.target` | `fixtures/buggy_cart` | File or directory to review |
| `panel.model` | `openai/gpt-5.6-sol` | Model ref for every panel member |
| `panel.max-findings-per-lens` | `4` | Round-1 cap per lens |
| `panel.max-candidates` | `8` | Candidates carried into round 2 |
| `panel.refuters-per-finding` | `3` | Independent attackers per finding |
| `panel.min-votes` | `2` | Verdicts needed before survival counts |
| `panel.canary` | `true` | Run the calibration probe |
| `agent.input` | `""` | Optional focus hint, honoured within each mandate |

Round 1 costs 5 calls and round 2 costs up to `max-candidates × refuters`, all
parallel. Defaults sit inside SuperGrid's 5-minute task timeout.

## The demo target

`fixtures/buggy_cart` is a small cart service holding real defects — SQL
injection, a mutable default argument, a swallowed exception, an N+1 query, a
dropped tax class — alongside code that *pattern-matches* as defective but holds
up under scrutiny.

The traps are deliberately unlabelled. An earlier version commented them
("parameterised, only looks like string-built SQL"), which told the reviewers the
answer and left round 2 with nothing to reject.

## Tests

```bash
PYTHONPATH=. python tests/test_panel.py
```

46 offline checks over the parts that decide what counts as evidence: dedupe,
vote accounting, the min-votes gate, refuter assignment, path containment, and
the canary. No model calls.

## Layout

```
review_panel/agent_app.py   orchestration, dedupe, vote accounting, report
review_panel/lenses.py      the five mandates and both rounds' prompts
review_panel/model.py       runtime-bound OpenAI client, JSON schemas
fixtures/buggy_cart/        demo target: real defects and unlabelled traps
tests/test_panel.py         offline checks
frontend/                   Next.js design system (App Router)
```

## Built on

Flower 1.35.0 AgentApp, running on SuperGrid. Round-1 and round-2 calls fan out
across threads; each `responses.create` opens its own child model task in the
Flower runtime, so the panel is genuinely concurrent rather than a loop of
sequential calls in one process.
