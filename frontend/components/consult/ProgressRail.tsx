import { STAGES } from "@/lib/consultScript";

type ProgressRailProps = {
  current: number; // -1 = nothing started
};

export function ProgressRail({ current }: ProgressRailProps) {
  return (
    <nav aria-label="Consult progress" className="border-b border-nhs-grey-4 bg-white">
      <ol className="mx-auto flex max-w-[1400px] overflow-x-auto px-5">
        {STAGES.map((s, i) => {
          const isOn = i === current;
          const isDone = i < current;
          return (
            <li
              key={s.label}
              className={[
                "min-w-[132px] flex-1 border-b-4 px-3.5 py-3",
                isOn ? "border-nhs-blue" : isDone ? "border-nhs-green" : "border-nhs-grey-4",
              ].join(" ")}
            >
              <p
                className={[
                  "text-[11px] uppercase tracking-[0.09em]",
                  isOn ? "font-semibold text-nhs-blue" : "text-nhs-grey-2",
                ].join(" ")}
              >
                {s.label}
                {isDone ? <span className="text-nhs-green"> ✓</span> : null}
              </p>
              <p
                className={[
                  "text-[13px] leading-tight",
                  isOn ? "font-semibold text-nhs-ink" : "text-nhs-grey-1",
                ].join(" ")}
              >
                {s.detail}
              </p>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
