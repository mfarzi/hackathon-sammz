import { CANDIDATES } from "@/lib/consultScript";
import { CandidateCard } from "./CandidateCard";

export function ReportMessage() {
  return (
    <>
      <p>
        <strong className="font-semibold">No single site could have reached this.</strong> The
        strongest match holds 2 cases; three other sites hold 1, 1 and 3. Ranking used the mean
        of the top three similarity scores network-wide, so case count never inflated a common
        diagnosis.
      </p>
      <div className="mt-3">
        {CANDIDATES.map((c) => (
          <CandidateCard key={c.name} candidate={c} />
        ))}
      </div>
      <p>
        Killed candidates are shown rather than hidden, so you can see what was considered and why
        it failed.
      </p>
    </>
  );
}
