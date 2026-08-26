import type { Site } from "@/lib/consultScript";

export type NodeStatus = "idle" | "searching" | "answered" | "no-data" | "follow-up";

const STATUS_TEXT: Record<NodeStatus, string> = {
  idle: "Idle",
  searching: "Searching",
  answered: "Answered",
  "no-data": "No data",
  "follow-up": "Follow-up",
};

const STATUS_CLASS: Record<NodeStatus, { border: string; text: string; bg?: string }> = {
  idle: { border: "border-l-nhs-grey-4", text: "text-nhs-grey-2" },
  searching: { border: "border-l-nhs-aqua", text: "text-nhs-aqua" },
  answered: { border: "border-l-nhs-green", text: "text-nhs-green", bg: "bg-nhs-green-soft" },
  "no-data": { border: "border-l-nhs-grey-2", text: "text-nhs-grey-1", bg: "bg-nhs-grey-5" },
  "follow-up": { border: "border-l-nhs-yellow", text: "text-nhs-yellow-ink", bg: "bg-nhs-yellow-soft" },
};

type SiteNodeProps = {
  site: Site;
  status: NodeStatus;
  matchLabel?: string;
  matchPct?: number;
};

export function SiteNode({ site, status, matchLabel, matchPct }: SiteNodeProps) {
  const cls = STATUS_CLASS[status];

  return (
    <div
      className={[
        "border-b border-l-4 border-nhs-grey-4 px-4 py-3.5 last:border-b-0",
        cls.border,
        cls.bg ?? "",
      ].join(" ")}
    >
      <div className="flex items-center gap-2">
        <strong className="text-[14px] font-semibold text-nhs-ink">{site.name}</strong>
        <span
          className={[
            "ml-auto whitespace-nowrap text-[11px] font-bold uppercase tracking-[0.07em]",
            cls.text,
          ].join(" ")}
        >
          {status === "searching" ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 animate-pulse-dot rounded-full bg-nhs-aqua" />
              {STATUS_TEXT[status]}
            </span>
          ) : (
            STATUS_TEXT[status]
          )}
        </span>
      </div>
      <p className="mt-0.5 text-[12px] text-nhs-grey-1">{site.subtitle}</p>
      {matchLabel ? (
        <>
          <p className="mt-2 font-mono text-[12px] text-nhs-grey-1">{matchLabel}</p>
          <div className="mt-1.5 h-1.5 overflow-hidden bg-nhs-grey-4">
            <div
              className="h-full bg-nhs-blue transition-[width] duration-500"
              style={{ width: `${matchPct ?? 0}%` }}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
