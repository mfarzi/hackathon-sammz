import type { Candidate, LensVerdict } from "@/lib/consultScript";

const TAG_CLASS: Record<Candidate["tag"], string> = {
  survived: "bg-nhs-green text-white",
  killed: "bg-nhs-red text-white",
  unverified: "bg-nhs-grey-1 text-white",
  planted: "bg-nhs-dark text-white",
};

const VERDICT_CLASS: Record<LensVerdict, string> = {
  holds: "text-nhs-green",
  refutes: "text-nhs-red",
  dissents: "text-nhs-red",
  abstain: "text-nhs-grey-2",
};

const VERDICT_LABEL: Record<LensVerdict, string> = {
  holds: "holds",
  refutes: "refutes",
  dissents: "dissents",
  abstain: "no verdict",
};

export function CandidateCard({ candidate }: { candidate: Candidate }) {
  return (
    <div className="mb-2.5 border border-nhs-grey-4">
      <div className="flex flex-wrap items-center gap-[11px] px-[14px] py-[11px]">
        <strong className="text-[15px] font-semibold text-nhs-ink">{candidate.name}</strong>
        <span
          className={[
            "px-[7px] py-[3px] text-[11px] font-bold uppercase tracking-[0.06em]",
            TAG_CLASS[candidate.tag],
          ].join(" ")}
        >
          {candidate.tagLabel}
        </span>
        <span className="ml-auto font-mono text-[13px] text-nhs-grey-1">{candidate.score}</span>
      </div>
      <div className="border-t border-nhs-grey-4 px-[14px] pb-3 pt-[11px] text-[14px] text-nhs-grey-1">
        <p>{candidate.body}</p>
        <p className="mt-[7px] font-mono text-[12px] text-nhs-grey-1">{candidate.provenance}</p>
        {candidate.dissent ? (
          <p className="mt-[9px] border-l-[3px] border-nhs-yellow pl-[10px] text-[13px] leading-snug">
            {candidate.dissent}
          </p>
        ) : null}
        <div className="mt-[10px] grid grid-cols-2 gap-px bg-nhs-grey-4 sm:grid-cols-3 lg:grid-cols-5">
          {candidate.lenses.map((l) => (
            <div key={l.label} className="bg-white px-[11px] py-[9px]">
              <b className="mb-[3px] block text-[10px] uppercase tracking-[0.08em] text-nhs-grey-1">
                {l.label}
              </b>
              <span className={["text-[12px] font-bold", VERDICT_CLASS[l.verdict]].join(" ")}>
                {VERDICT_LABEL[l.verdict]}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
