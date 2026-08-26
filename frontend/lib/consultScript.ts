/**
 * Fixture data for one Rare Disease Consult Network run.
 * Ported from the standalone HTML demo — same case, same network, same
 * timings — so the React thread reads identically until a real hub agent
 * is wired in behind this shape.
 */

export type SiteId = "H1" | "H2" | "H3" | "H4" | "H5";

export interface Site {
  id: SiteId;
  name: string;
  subtitle: string;
}

export const SITES: Site[] = [
  { id: "H1", name: "Royal Infirmary", subtitle: "Urban teaching · 26,149 records" },
  { id: "H2", name: "Riverbend Rural", subtitle: "District general · 5,203 records" },
  { id: "H3", name: "Cardiac Institute", subtitle: "Specialist centre · 10,057 records" },
  { id: "H4", name: "Children's Hospital", subtitle: "Paediatric · 11,532 records" },
  { id: "H5", name: "Regional Hospital", subtitle: "Regional · 22,060 records" },
];

export const CASE_TEXT =
  "Man in his 40s, six weeks of nosebleeds and persistent nasal crusting, now coughing blood. " +
  "Urine dip shows blood. Sinus pain throughout. Two courses of antibiotics, no response.";

export const PARSED_QUERY: { label: string; value: string }[] = [
  { label: "symptoms", value: "epistaxis · nasal_crusting · haemoptysis · haematuria · sinus_pain" },
  { label: "age_bracket", value: "41-50" },
  { label: "gender", value: "M" },
  { label: "excluded", value: "record_id, free text, anything identifying" },
];

export interface WireItem {
  label: string;
  value: string;
}

export interface SiteReply {
  id: SiteId;
  caseCount: number;
  matchPct: number;
  delayMs: number;
  hasData: boolean;
  statusLabel: string;
  headline: string;
  paragraphs: string[];
  sent: WireItem[];
  held: string[];
}

export const REPLIES: SiteReply[] = [
  {
    id: "H3",
    caseCount: 0,
    matchPct: 0,
    delayMs: 500,
    hasData: false,
    statusLabel: "No data",
    headline: "Cardiac Institute — no comparable cases.",
    paragraphs: [
      "Nothing in our records combines upper airway disease with renal findings. Our corpus is cardiac; treat this as a genuine absence, not a gap in coverage.",
    ],
    sent: [
      { label: "disease_match", value: "none" },
      { label: "cases_found", value: "0" },
      { label: "note", value: "out-of-domain corpus" },
    ],
    held: ["10,057 record_ids", "every free-text note"],
  },
  {
    id: "H2",
    caseCount: 1,
    matchPct: 22,
    delayMs: 900,
    hasData: true,
    statusLabel: "1 case",
    headline: "Riverbend Rural — 1 comparable case.",
    paragraphs: [
      "Middle-aged man, nasal crusting and repeated nosebleeds over two months, treated twice as sinusitis with no response. Developed frank haematuria. Referred out before a diagnosis was reached here, so our record ends unresolved.",
      "Notably absent: no fever, no weight loss recorded at any visit.",
    ],
    sent: [
      { label: "disease_match", value: "granulomatosis_with_polyangiitis (suspected)" },
      { label: "cases_found", value: "1" },
      { label: "similarity", value: "0.84" },
      { label: "abstraction", value: "62 words, written by this site's agent" },
    ],
    held: ["record_id 4A11C7", "the note itself", "referral letter text"],
  },
  {
    id: "H4",
    caseCount: 1,
    matchPct: 20,
    delayMs: 700,
    hasData: true,
    statusLabel: "1 case",
    headline: "Children's Hospital — 1 comparable case.",
    paragraphs: [
      "Adolescent, saddle-nose deformity following long-standing nasal disease, with microscopic haematuria found on screening. Confirmed on biopsy.",
      "Argues against the alternatives: no anti-GBM antibodies on testing.",
    ],
    sent: [
      { label: "disease_match", value: "granulomatosis_with_polyangiitis (confirmed)" },
      { label: "cases_found", value: "1" },
      { label: "similarity", value: "0.79" },
      { label: "abstraction", value: "48 words, written by this site's agent" },
    ],
    held: ["record_id 9C0E32", "the note itself", "biopsy report"],
  },
  {
    id: "H1",
    caseCount: 2,
    matchPct: 44,
    delayMs: 1000,
    hasData: true,
    statusLabel: "2 cases",
    headline: "Royal Infirmary — 2 comparable cases.",
    paragraphs: [
      "Both presented with upper airway disease preceding renal involvement by several weeks. In both, the nasal symptoms were treated as infection first. One had haemoptysis, the other did not.",
      "Course in both: weeks, not days. Neither improved on antibiotics.",
    ],
    sent: [
      { label: "disease_match", value: "granulomatosis_with_polyangiitis (confirmed)" },
      { label: "cases_found", value: "2" },
      { label: "similarity", value: "0.91, 0.86" },
      { label: "abstraction", value: "71 words, written by this site's agent" },
    ],
    held: ["record_ids 7F3A2C, B22D90", "both notes", "all imaging"],
  },
  {
    id: "H5",
    caseCount: 3,
    matchPct: 66,
    delayMs: 1200,
    hasData: true,
    statusLabel: "3 cases",
    headline: "Regional Hospital — 3 comparable cases.",
    paragraphs: [
      "Three with sinonasal disease and haematuria. Two confirmed vasculitis; one turned out to be tuberculosis with incidental renal stones, which is worth flagging as a mimic in our setting.",
      "Endemic caution: we would not exclude TB on this presentation alone.",
    ],
    sent: [
      { label: "disease_match", value: "granulomatosis_with_polyangiitis (2 confirmed)" },
      { label: "cases_found", value: "3" },
      { label: "similarity", value: "0.88, 0.81, 0.55" },
      { label: "counter-note", value: "TB mimic, 1 case" },
    ],
    held: ["3 record_ids", "all three notes", "sputum results"],
  },
];

export const FOLLOW_UP = {
  targets: ["H1", "H4", "H5"] as SiteId[],
  reasoning:
    "Three sites describe upper airway disease before renal involvement. That fits several vasculitides equally well, so it does not discriminate. What separates them is whether the renal picture is a true glomerulonephritis, and how fast it moved.",
  question:
    "Did the renal involvement show an active urinary sediment, and how many weeks from first nasal symptom to renal finding?",
  answers: [
    { site: "Royal Infirmary", answer: "Active sediment in both. 5 and 7 weeks." },
    { site: "Children's Hospital", answer: "Active sediment. Roughly 9 weeks." },
    {
      site: "Regional Hospital",
      answer:
        "Active sediment in the two confirmed cases; the TB mimic had a bland sediment, which is what separated it.",
    },
  ],
  sent: [
    { label: "sediment", value: "active ×4" },
    { label: "weeks_to_renal", value: "5, 7, ~9" },
    { label: "note", value: "mimic excluded on sediment" },
  ],
  held: ["urinalysis reports", "all notes", "record_ids"],
};

export type LensVerdict = "holds" | "refutes" | "dissents" | "abstain";

export interface Candidate {
  name: string;
  score: string;
  tag: "survived" | "unverified" | "killed" | "planted";
  tagLabel: string;
  body: string;
  provenance: string;
  dissent?: string;
  lenses: { label: string; verdict: LensVerdict }[];
}

export const CANDIDATES: Candidate[] = [
  {
    name: "Granulomatosis with polyangiitis",
    score: "0.87",
    tag: "survived",
    tagLabel: "Survived",
    body: "Held against all three refuters. Upper airway disease preceding active glomerulonephritis over weeks, unresponsive to antibiotics, matches 6 of 7 network cases.",
    provenance: "top-3 mean 0.87 · 6 cases across 4 sites · no site held more than 3",
    dissent:
      "Dissent carried: the negative-findings reviewer notes no site reported ANCA status, so serology is assumed rather than shown.",
    lenses: [
      { label: "Symptom fit", verdict: "holds" },
      { label: "Contradicting evidence", verdict: "dissents" },
      { label: "Demographic plausibility", verdict: "holds" },
      { label: "Common explanations", verdict: "holds" },
      { label: "Evidence quality", verdict: "holds" },
    ],
  },
  {
    name: "Microscopic polyangiitis",
    score: "0.71",
    tag: "unverified",
    tagLabel: "Unverified",
    body: "Only two reviewers returned a verdict before the round closed. Not read as agreement.",
    provenance: "top-3 mean 0.71 · 2 cases across 2 sites",
    lenses: [
      { label: "Symptom fit", verdict: "abstain" },
      { label: "Contradicting evidence", verdict: "holds" },
      { label: "Demographic plausibility", verdict: "abstain" },
      { label: "Common explanations", verdict: "refutes" },
      { label: "Evidence quality", verdict: "abstain" },
    ],
  },
  {
    name: "Anti-GBM disease",
    score: "0.68",
    tag: "killed",
    tagLabel: "Killed",
    body: "Refuted 3–0. The Children's Hospital case tested negative for anti-GBM antibodies, and the sinonasal disease preceding renal involvement by weeks does not fit the usual course.",
    provenance: "top-3 mean 0.68 · 1 case, 1 site",
    lenses: [
      { label: "Symptom fit", verdict: "refutes" },
      { label: "Contradicting evidence", verdict: "refutes" },
      { label: "Demographic plausibility", verdict: "holds" },
      { label: "Common explanations", verdict: "refutes" },
      { label: "Evidence quality", verdict: "abstain" },
    ],
  },
  {
    name: "Seasonal vasculitic nephropathy",
    score: "0.66",
    tag: "planted",
    tagLabel: "Planted probe · killed",
    body: "Not a real entity. Inserted indistinguishably to test whether the panel can still say no. Rejected 3–0 for having no case series behind it at any site.",
    provenance: "calibration probe · never counted toward the diagnosis",
    lenses: [
      { label: "Symptom fit", verdict: "refutes" },
      { label: "Contradicting evidence", verdict: "refutes" },
      { label: "Demographic plausibility", verdict: "abstain" },
      { label: "Common explanations", verdict: "refutes" },
      { label: "Evidence quality", verdict: "refutes" },
    ],
  },
];

export const STAGES = [
  { label: "Stage 1", detail: "Case described" },
  { label: "Stage 2", detail: "Query fanned out" },
  { label: "Stage 3", detail: "Sites read own notes" },
  { label: "Stage 4", detail: "Follow-up asked" },
  { label: "Stage 5", detail: "Panel attacks" },
  { label: "Stage 6", detail: "Report returned" },
] as const;
