import type { Candidate, LensVerdict } from "@/lib/consultScript";

const TAG_CLASS: Record<Candidate["tag"], string> = {
  survived: "bg-stay text-paper-raised",
  killed: "bg-leave text-paper-raised",
  unverified: "bg-ink-muted text-paper-raised",
  planted: "bg-instrument text-instrument-ink",
};

const VERDICT_CLASS: Record<LensVerdict, string> = {
  holds: "text-stay",
  refutes: "text-leave",
  dissents: "text-leave",
  abstain: "text-ink-faint",
};

const VERDICT_LABEL: Record<LensVerdict, string> = {
  holds: "holds",
  refutes: "refutes",
  dissents: "dissents",
  abstain: "no verdict",
};

export function CandidateCard({ candidate }: { candidate: Candidate }) {
  return (
    <div className="mb-3 border border-rule bg-paper">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3">
        <strong className="font-serif text-[16px] font-normal text-ink">{candidate.name}</strong>
        <span
          className={[
            "px-2 py-0.5 font-mono text-[10.5px] font-bold uppercase tracking-[0.06em]",
            TAG_CLASS[candidate.tag],
          ].join(" ")}
        >
          {candidate.tagLabel}
        </span>
        <span className="ml-auto font-mono text-[13px] text-ink-muted">{candidate.score}</span>
      </div>
      <div className="border-t border-rule px-4 py-3.5">
        <p className="font-serif text-[14.5px] leading-relaxed text-ink-muted">{candidate.body}</p>
        <p className="mt-2 font-mono text-[11.5px] text-ink-faint">{candidate.provenance}</p>
        {candidate.dissent ? (
          <p className="mt-2.5 border-l-2 border-ask pl-2.5 font-serif text-[13.5px] leading-snug text-ink-muted">
            {candidate.dissent}
          </p>
        ) : null}
        <div className="mt-3 grid grid-cols-2 gap-px bg-rule sm:grid-cols-3 lg:grid-cols-5">
          {candidate.lenses.map((l) => (
            <div key={l.label} className="bg-paper-raised px-2.5 py-2">
              <b className="block font-mono text-[9.5px] uppercase tracking-[0.07em] text-ink-muted">
                {l.label}
              </b>
              <span className={["font-mono text-[12px] font-semibold", VERDICT_CLASS[l.verdict]].join(" ")}>
                {VERDICT_LABEL[l.verdict]}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
