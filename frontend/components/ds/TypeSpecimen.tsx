import { Button } from "./Button";
import { CodeChip } from "./CodeChip";
import { DisclosureRail } from "./DisclosureRail";
import { Panel } from "./Panel";

const swatches = [
  { name: "paper", className: "bg-paper border border-rule", hex: "#F4EFE6" },
  {
    name: "paper-raised",
    className: "bg-paper-raised border border-rule",
    hex: "#FAF7F1",
  },
  { name: "ink", className: "bg-ink", hex: "#1C1917" },
  { name: "ink-muted", className: "bg-ink-muted", hex: "#57534E" },
  { name: "stay", className: "bg-stay", hex: "#3F4A3C" },
  { name: "leave", className: "bg-leave", hex: "#9A3412" },
  { name: "instrument", className: "bg-instrument", hex: "#1A1814" },
] as const;

export function TypeSpecimen() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10 sm:px-10 sm:py-14">
      <header className="border-b border-rule pb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          Adversarial Review Panel · Design system 0.1
        </p>
        <h1 className="mt-3 max-w-2xl font-serif text-[32px] leading-[1.15] tracking-tight text-ink text-balance sm:text-[40px]">
          Clinical instrument
        </h1>
        <p className="mt-4 max-w-xl font-serif text-[16px] leading-relaxed text-ink-muted">
          Quiet, high-trust surfaces for a blind multi-lens review. Findings are
          attributable. Dissent survives. Calibration is visible.
        </p>
      </header>

      <section className="mt-10 grid gap-10">
        <div>
          <SectionLabel n="01" title="Colour" />
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
            {swatches.map((s) => (
              <div key={s.name} className="min-w-0">
                <div className={`aspect-[4/3] ${s.className}`} />
                <p className="mt-2 font-mono text-[11px] text-ink">{s.name}</p>
                <p className="font-mono text-[10px] text-ink-faint">{s.hex}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <SectionLabel n="02" title="Type" />
          <div className="mt-4 grid gap-6 sm:grid-cols-2">
            <Panel eyebrow="Serif · Libre Baskerville" title="Finding prose">
              <p className="font-serif text-[15px] leading-[1.65] text-ink">
                SQL injection in{" "}
                <span className="font-mono text-[13px]">cart/db.py</span>: query
                string is built with f-strings from request parameters. Round-2
                refuters did not kill this claim.
              </p>
            </Panel>
            <Panel eyebrow="Mono · IBM Plex Mono" title="Lenses & votes">
              <pre className="overflow-x-auto font-mono text-[12px] leading-relaxed text-ink">
                {`lens        mandate
──────────  ────────────
correctness logic / bugs
security    injection / auth
performance N+1 / hot paths
robustness  errors / edge
contracts   APIs / types`}
              </pre>
            </Panel>
          </div>
        </div>

        <div>
          <SectionLabel n="03" title="Status chips" />
          <div className="mt-4 flex flex-wrap gap-2">
            <CodeChip id="F-01" label="Candidate" />
            <CodeChip id="F-02" label="Survived" state="accepted" />
            <CodeChip id="F-03" label="Killed" state="rejected" />
            <CodeChip id="CANARY" label="Calibration" state="leaving" />
          </div>
        </div>

        <div>
          <SectionLabel n="04" title="Buttons" />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="primary">Run panel</Button>
            <Button variant="secondary">Load fixture</Button>
            <Button variant="leave">Show killed</Button>
            <Button variant="ghost">Cancel</Button>
          </div>
        </div>

        <div>
          <SectionLabel n="05" title="Verdict rail" />
          <div className="mt-4">
            <DisclosureRail
              stayTitle="Kept in report"
              leaveTitle="Shown as rejected"
              stays={[
                {
                  label: "Survivors",
                  detail: "Findings that survived majority refutation",
                },
                {
                  label: "Dissent",
                  detail: "1-of-3 splits are never shown as unanimous",
                },
                {
                  label: "Attribution",
                  detail: "Which lens raised it; who attacked it",
                },
              ]}
              leaves={[
                {
                  label: "Killed findings",
                  detail: "Shown, not hidden — trust comes from what died",
                },
                {
                  label: "Calibration probe",
                  detail: "Known-false canary; if it survives, distrust the run",
                },
              ]}
            />
          </div>
        </div>

        <div>
          <SectionLabel n="06" title="Instrument panel" />
          <div className="mt-4">
            <Panel
              tone="instrument"
              eyebrow="Round 2 · refutation"
              title="Blind attackers · 3 lenses"
            >
              <pre className="overflow-x-auto font-mono text-[12px] leading-relaxed text-instrument-ink">
                {`[master]   candidates=6  canary=on
[security] F-02 refuted — parameterised query, false positive pattern
[robust.]  F-02 stands — empty except block still swallows IntegrityError
[contracts] F-02 stands — vote=stands  (2/3)
[panel]    F-02 SURVIVED with dissent`}
              </pre>
            </Panel>
          </div>
        </div>
      </section>

      <footer className="mt-14 border-t border-rule pt-6">
        <p className="font-mono text-[11px] text-ink-faint">
          Five blind lenses. Then refute. Frontend owns this folder; agent code
          lives in review_panel/.
        </p>
      </footer>
    </div>
  );
}

function SectionLabel({ n, title }: { n: string; title: string }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="font-mono text-[11px] tabular-nums text-ink-faint">
        {n}
      </span>
      <h2 className="font-serif text-[18px] text-ink">{title}</h2>
    </div>
  );
}
