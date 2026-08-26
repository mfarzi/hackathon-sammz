import { STAGES } from "@/lib/consultScript";

type ProgressRailProps = {
  current: number; // -1 = nothing started
};

export function ProgressRail({ current }: ProgressRailProps) {
  return (
    <nav aria-label="Consult progress" className="border border-rule bg-paper-raised">
      <ol className="flex overflow-x-auto">
        {STAGES.map((s, i) => {
          const isOn = i === current;
          const isDone = i < current;
          return (
            <li
              key={s.label}
              className={[
                "min-w-[132px] flex-1 border-b-4 px-3.5 py-3",
                isOn ? "border-ink" : isDone ? "border-stay" : "border-rule",
              ].join(" ")}
            >
              <p
                className={[
                  "font-mono text-[10px] uppercase tracking-[0.14em]",
                  isOn ? "text-ink" : isDone ? "text-stay" : "text-ink-faint",
                ].join(" ")}
              >
                {s.label}
                {isDone ? " ✓" : ""}
              </p>
              <p
                className={[
                  "mt-0.5 font-serif text-[13px] leading-tight",
                  isOn ? "font-medium text-ink" : "text-ink-muted",
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
