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
  idle: { border: "border-l-rule", text: "text-ink-faint" },
  searching: { border: "border-l-wait", text: "text-wait" },
  answered: { border: "border-l-stay", text: "text-stay", bg: "bg-stay-soft" },
  "no-data": { border: "border-l-ink-faint", text: "text-ink-muted", bg: "bg-paper" },
  "follow-up": { border: "border-l-ask", text: "text-ask", bg: "bg-ask-soft" },
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
      className={["border-b border-l-4 border-rule px-4 py-3.5", cls.border, cls.bg ?? ""].join(
        " ",
      )}
    >
      <div className="flex items-center gap-2">
        <strong className="font-serif text-[14px] font-normal text-ink">{site.name}</strong>
        <span
          className={[
            "ml-auto whitespace-nowrap font-mono text-[11px] font-medium uppercase tracking-[0.07em]",
            cls.text,
          ].join(" ")}
        >
          {status === "searching" ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-1.5 w-1.5 animate-pulse-dot rounded-full bg-wait" />
              {STATUS_TEXT[status]}
            </span>
          ) : (
            STATUS_TEXT[status]
          )}
        </span>
      </div>
      <p className="mt-0.5 font-mono text-[11px] text-ink-muted">{site.subtitle}</p>
      {matchLabel ? (
        <>
          <p className="mt-2 font-mono text-[12px] text-ink-muted">{matchLabel}</p>
          <div className="mt-1.5 h-1.5 bg-rule">
            <div
              className="h-full bg-ink transition-[width] duration-500"
              style={{ width: `${matchPct ?? 0}%` }}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
