const ANSI = /\x1b\[[0-9;]*m/g;

export type LiveLine = {
  key: number;
  kind: "hub" | "panel" | "site" | "rule" | "error" | "report" | "plain";
  tag?: string;
  text: string;
};

/**
 * Classify one already-filtered line from `ask` into a kind for styling.
 *
 * `ask` (see ../../../ask) does the real filtering — dropping runtime noise,
 * collapsing ray's actor-pid prefixes — before it ever prints a line. This
 * only has to recognise the shape of what it already chose to show: `hub  `,
 * `panel  `, `<site>  `, the dashed rule that opens the report, and errors.
 */
export function classifyLine(raw: string, reportStarted: boolean): Omit<LiveLine, "key"> {
  const clean = raw.replace(ANSI, "").replace(/\r$/, "");
  const trimmed = clean.trimEnd();

  if (!trimmed.trim()) return { kind: "plain", text: "" };

  if (/^─{5,}$/.test(trimmed.trim())) {
    return { kind: "rule", text: trimmed.trim() };
  }
  if (trimmed.startsWith("hub  ")) {
    return { kind: "hub", tag: "hub", text: trimmed.slice(5).trim() };
  }
  if (trimmed.startsWith("panel  ")) {
    return { kind: "panel", tag: "panel", text: trimmed.slice(7).trim() };
  }
  const siteMatch = trimmed.match(/^(hospital_\d+)\s\s(.*)$/);
  if (siteMatch) {
    return { kind: "site", tag: siteMatch[1], text: siteMatch[2].trim() };
  }
  if (
    trimmed.includes("ERROR") ||
    trimmed.includes("Traceback") ||
    trimmed.startsWith("Exit Code") ||
    trimmed.startsWith("[failed to start") ||
    trimmed.startsWith("[process exited with code 1")
  ) {
    return { kind: "error", text: trimmed };
  }
  if (reportStarted) {
    return { kind: "report", text: clean };
  }
  return { kind: "plain", text: trimmed };
}

const KIND_STYLES: Record<LiveLine["kind"], string> = {
  hub: "text-ink",
  panel: "text-ink-muted",
  site: "text-ink-muted",
  rule: "text-ink-faint",
  error: "text-red-700",
  report: "text-ink",
  plain: "text-ink-faint",
};

const TAG_STYLES: Record<LiveLine["kind"], string> = {
  hub: "text-ink",
  panel: "text-ask",
  site: "text-wait",
  rule: "",
  error: "",
  report: "",
  plain: "",
};

/** Turn `**bold**` spans into <strong>, leaving everything else as plain text. */
function renderInline(text: string, keyPrefix: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${i}`} className="font-semibold text-ink">
        {part.slice(2, -2)}
      </strong>
    ) : (
      part
    ),
  );
}

/**
 * The master's report arrives as real markdown. This is the one part of the
 * output a clinician actually reads, so it earns the same serif prose
 * treatment as the rest of the app rather than staying in the log's
 * monospace voice - just enough structure (headings, bullets, bold) to read
 * as a finished report instead of raw text with asterisks in it.
 */
export function ReportLine({ text, id }: { text: string; id: number }) {
  if (text.startsWith("### ")) {
    return (
      <h4 key={id} className="mt-3 font-serif text-[14px] font-semibold text-ink">
        {renderInline(text.slice(4), `h4-${id}`)}
      </h4>
    );
  }
  if (text.startsWith("## ")) {
    return (
      <h3
        key={id}
        className="mt-4 border-t border-rule pt-3 font-serif text-[16px] font-semibold text-ink"
      >
        {renderInline(text.slice(3), `h3-${id}`)}
      </h3>
    );
  }
  if (text.startsWith("- ")) {
    return (
      <div key={id} className="mt-1 flex gap-2 font-serif text-[13.5px] leading-relaxed text-ink-muted">
        <span className="text-ink-faint">–</span>
        <span>{renderInline(text.slice(2), `li-${id}`)}</span>
      </div>
    );
  }
  return (
    <p key={id} className="mt-2 font-serif text-[13.5px] leading-relaxed text-ink-muted">
      {renderInline(text, `p-${id}`)}
    </p>
  );
}

export function LiveLogLine({ line }: { line: LiveLine }) {
  if (line.kind === "rule") {
    return <div className="my-2 border-t border-rule" />;
  }
  if (!line.text) return null;

  if (line.kind === "report") {
    return <ReportLine text={line.text} id={line.key} />;
  }

  return (
    <div className={`whitespace-pre-wrap ${KIND_STYLES[line.kind]}`}>
      {line.tag && (
        <span className={`font-semibold ${TAG_STYLES[line.kind]}`}>{line.tag}</span>
      )}
      {/* A real space, not a CSS margin: margin creates a visual gap but
          leaves zero characters in the DOM, so copying the log as text glues
          the tag onto the body with nothing between them. */}
      {line.tag ? "  " : ""}
      {line.text}
    </div>
  );
}
