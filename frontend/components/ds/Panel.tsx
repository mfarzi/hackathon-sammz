import type { HTMLAttributes, ReactNode } from "react";

type PanelProps = HTMLAttributes<HTMLElement> & {
  title?: string;
  eyebrow?: string;
  tone?: "paper" | "instrument";
  children: ReactNode;
};

export function Panel({
  title,
  eyebrow,
  tone = "paper",
  children,
  className = "",
  ...props
}: PanelProps) {
  const isInstrument = tone === "instrument";

  return (
    <section
      className={[
        "border",
        isInstrument
          ? "border-instrument bg-instrument text-instrument-ink"
          : "border-rule bg-paper-raised text-ink",
        className,
      ].join(" ")}
      {...props}
    >
      {(eyebrow || title) && (
        <header
          className={[
            "flex items-baseline justify-between gap-4 border-b px-4 py-3",
            isInstrument ? "border-instrument-muted/30" : "border-rule",
          ].join(" ")}
        >
          <div className="min-w-0">
            {eyebrow ? (
              <p
                className={[
                  "font-mono text-[10px] uppercase tracking-[0.14em]",
                  isInstrument ? "text-instrument-muted" : "text-ink-faint",
                ].join(" ")}
              >
                {eyebrow}
              </p>
            ) : null}
            {title ? (
              <h2
                className={[
                  "mt-0.5 font-serif text-[15px] font-normal leading-tight",
                  isInstrument ? "text-instrument-ink" : "text-ink",
                ].join(" ")}
              >
                {title}
              </h2>
            ) : null}
          </div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
