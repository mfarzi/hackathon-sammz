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

export function LiveLogLine({ line }: { line: LiveLine }) {
  if (line.kind === "rule") {
    return <div className="my-2 border-t border-rule" />;
  }
  if (!line.text) return null;

  return (
    <div className={`whitespace-pre-wrap ${KIND_STYLES[line.kind]}`}>
      {line.tag && (
        <span className={`mr-2 font-semibold ${TAG_STYLES[line.kind]}`}>{line.tag}</span>
      )}
      {line.text}
    </div>
  );
}
