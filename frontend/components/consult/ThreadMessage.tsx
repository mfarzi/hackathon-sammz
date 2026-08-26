import type { ReactNode } from "react";

export type MessageRole = "clinician" | "hub" | "site" | "site-nodata" | "sys";

const ROLE_CLASS: Record<MessageRole, string> = {
  clinician: "border-ink bg-ink text-paper-raised border-l-ink",
  hub: "border-rule bg-paper-raised text-ink border-l-wait",
  site: "border-rule bg-paper-raised text-ink border-l-stay",
  "site-nodata": "border-rule bg-paper text-ink-muted border-l-ink-faint",
  sys: "border-rule bg-ask-soft text-ink border-l-ask",
};

type ThreadMessageProps = {
  who: string;
  role: MessageRole;
  children: ReactNode;
};

export function ThreadMessage({ who, role, children }: ThreadMessageProps) {
  const isClinician = role === "clinician";

  return (
    <div className={["mb-5 max-w-[720px]", isClinician ? "ml-auto" : ""].join(" ")}>
      <p
        className={[
          "mb-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.1em]",
          isClinician ? "text-right text-ink-muted" : "text-ink-muted",
        ].join(" ")}
      >
        {who}
      </p>
      <div className={["border border-l-4 px-4 py-3.5", ROLE_CLASS[role]].join(" ")}>
        <div className="space-y-2 font-serif text-[15px] leading-relaxed [&_p:last-child]:mb-0">
          {children}
        </div>
      </div>
    </div>
  );
}
