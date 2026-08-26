import type { ReactNode } from "react";

export type MessageRole = "clinician" | "hub" | "site" | "site-nodata" | "sys";

const ROLE_CLASS: Record<MessageRole, string> = {
  clinician: "border-nhs-blue bg-nhs-blue text-white",
  hub: "border-nhs-grey-4 bg-white text-nhs-ink border-l-nhs-blue",
  site: "border-nhs-grey-4 bg-white text-nhs-ink border-l-nhs-green",
  "site-nodata": "border-nhs-grey-4 bg-nhs-grey-5 text-nhs-grey-1 border-l-nhs-grey-2",
  sys: "border-nhs-grey-4 bg-nhs-yellow-soft text-nhs-ink border-l-nhs-yellow",
};

type ThreadMessageProps = {
  who: string;
  role: MessageRole;
  children: ReactNode;
};

export function ThreadMessage({ who, role, children }: ThreadMessageProps) {
  const isClinician = role === "clinician";

  return (
    <div className={["mb-[18px] max-w-[820px]", isClinician ? "ml-auto" : ""].join(" ")}>
      <p className="mb-[5px] text-[11px] font-bold uppercase tracking-[0.09em] text-nhs-grey-1">
        {who}
      </p>
      <div className={["border px-[15px] py-[13px]", isClinician ? "" : "border-l-4", ROLE_CLASS[role]].join(" ")}>
        <div className="space-y-2 text-[16px] leading-[1.5] [&_p:last-child]:mb-0">{children}</div>
      </div>
    </div>
  );
}
