type DisclosureItem = {
  label: string;
  detail?: string;
};

type DisclosureRailProps = {
  stays: DisclosureItem[];
  leaves: DisclosureItem[];
  stayTitle?: string;
  leaveTitle?: string;
};

function Column({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "stay" | "leave";
  items: DisclosureItem[];
}) {
  const isLeave = tone === "leave";

  return (
    <div
      className={[
        "flex-1 border-t-2 pt-3",
        isLeave ? "border-leave" : "border-stay",
      ].join(" ")}
    >
      <p
        className={[
          "font-mono text-[10px] uppercase tracking-[0.16em]",
          isLeave ? "text-leave" : "text-stay",
        ].join(" ")}
      >
        {title}
      </p>
      <ul className="mt-3 space-y-2.5">
        {items.map((item) => (
          <li key={item.label} className="min-w-0">
            <p className="font-serif text-[14px] leading-snug text-ink">
              {item.label}
            </p>
            {item.detail ? (
              <p className="mt-0.5 font-mono text-[11px] leading-snug text-ink-muted">
                {item.detail}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DisclosureRail({
  stays,
  leaves,
  stayTitle = "Stays on site",
  leaveTitle = "Leaves the building",
}: DisclosureRailProps) {
  return (
    <aside
      aria-label="Disclosure boundary"
      className="flex flex-col gap-6 border border-rule bg-paper-raised p-4 sm:flex-row sm:gap-8"
    >
      <Column title={stayTitle} tone="stay" items={stays} />
      <div
        className="hidden w-px self-stretch bg-rule sm:block"
        aria-hidden
      />
      <Column title={leaveTitle} tone="leave" items={leaves} />
    </aside>
  );
}
