# Frontend — Rare Disease Consult Network

Next.js App Router UI for the consult: a clinician describes a case, every
hospital node in the network answers from its own records, and a blind
review panel decides what survives.

Owns only this folder. Backend/agent code: `../review_panel/`.

## Run

```bash
cd frontend
npm install
npm run dev
```

- `/` — the consult app (`components/consult`). Currently runs a scripted
  fixture (`lib/consultScript.ts`) end to end on the same timing as the
  network/panel would produce, so the UI is ready to swap onto a real
  hub-agent feed without changing component shape.
- `/design-system` — the original token/type/component specimen page.

## Structure

- `app/` — layout, globals, the consult page, the design-system specimen page
- `components/consult/` — NetworkPanel, SiteNode, ProgressRail, ThreadMessage,
  WireBox, CandidateCard, CalibrationBanner, Composer, ConsultApp
- `components/ds/` — Button, CodeChip, Panel, DisclosureRail, TypeSpecimen
- `lib/consultScript.ts` — the fixture data driving one scripted run
- `lib/tokens.ts` — typed token names

## Wiring in the real backend

`ConsultApp` (`components/consult/ConsultApp.tsx`) currently drives its
timeline from the static fixture in `lib/consultScript.ts` with `setTimeout`
delays standing in for network round-trips. To wire it to the real hub agent,
replace the body of `run()` with calls into the backend (SSE/WebSocket/poll),
mapping each event onto the same `push(...)`, `setNode(...)`, `bump(...)`,
and `setStageIndex(...)` calls already used there — the presentational
components (`SiteReplyMessage`, `FollowUpAnswers`, `CandidateCard`, etc.)
don't need to change, only what feeds them.
