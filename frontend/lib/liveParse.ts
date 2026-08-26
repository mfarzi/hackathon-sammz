/**
 * Pure parsing of the real backend's streamed output.
 *
 * `../../ask` already filters runtime noise down to lines tagged `hub  `,
 * `panel  `, `<site>  `, a dashed rule opening the report, and errors. This
 * goes one level further: recognising the *shape* of specific hub/panel/site
 * lines (the ranked-candidate table, a follow-up question, a per-site answer,
 * a panel verdict, the calibration result) so a UI can render real structure
 * instead of a raw log. No JSX here - this stays framework-agnostic so both
 * the homepage's NHS-styled thread and any other consumer can parse the same
 * way and render however they like.
 */

const ANSI = /\x1b\[[0-9;]*m/g;

export type Tag = "hub" | "panel" | "site" | "rule" | "error" | "report" | "plain";

export type ClassifiedLine = { kind: Tag; tag?: string; text: string };

export function classifyLine(raw: string, reportStarted: boolean): ClassifiedLine {
  const clean = raw.replace(ANSI, "").replace(/\r$/, "");
  const trimmed = clean.trimEnd();

  if (!trimmed.trim()) return { kind: "plain", text: "" };
  if (/^─{5,}$/.test(trimmed.trim())) return { kind: "rule", text: trimmed.trim() };
  if (trimmed.startsWith("hub  ")) return { kind: "hub", tag: "hub", text: trimmed.slice(5).trim() };
  if (trimmed.startsWith("panel  ")) return { kind: "panel", tag: "panel", text: trimmed.slice(7).trim() };

  const siteMatch = trimmed.match(/^(hospital_\d+)\s\s(.*)$/);
  if (siteMatch) return { kind: "site", tag: siteMatch[1], text: siteMatch[2].trim() };

  if (
    trimmed.includes("ERROR") ||
    trimmed.includes("Traceback") ||
    trimmed.startsWith("Exit Code") ||
    trimmed.startsWith("[failed to start")
  ) {
    return { kind: "error", text: trimmed };
  }
  const exitMatch = trimmed.match(/^\[process exited with code (\d+)\]/);
  if (exitMatch && exitMatch[1] !== "0") return { kind: "error", text: trimmed };

  if (reportStarted) return { kind: "report", text: clean };
  return { kind: "plain", text: trimmed };
}

// --- sub-parsers for specific hub/panel line shapes -------------------------

export function parseSymptoms(hubText: string): string[] | null {
  const m = hubText.match(/^symptoms:\s*(.+)$/);
  return m ? m[1].split(",").map((s) => s.trim()) : null;
}

export function parseSitesOnline(hubText: string): number | null {
  const m = hubText.match(/^(\d+) hospital site\(s\) online$/);
  return m ? Number(m[1]) : null;
}

export type RankedRow = { disease: string; score: number; cases: number; sites: string[] };

export function isRankedHeader(hubText: string): boolean {
  return hubText.startsWith("ranked candidates");
}

export function parseRankedRow(hubText: string): RankedRow | null {
  const m = hubText.match(/^(\S+)\s+([\d.]+)\s+\|\s+(\d+)\s+\|\s+(.+)$/);
  if (!m) return null;
  return {
    disease: m[1],
    score: Number(m[2]),
    cases: Number(m[3]),
    sites: m[4].split(",").map((s) => s.trim()),
  };
}

export function parseSiteReplied(siteText: string): { count: number; matched: number } | null {
  const m = siteText.match(/^(\d+) records searched, (\d+) disease\(s\) matched$/);
  return m ? { count: Number(m[1]), matched: Number(m[2]) } : null;
}

export function parseFollowUpQuestion(
  hubText: string,
): { disease: string; question: string } | null {
  const m = hubText.match(/^follow-up on ([^:]+):\s*"(.+)"$/);
  return m ? { disease: m[1], question: m[2] } : null;
}

export function parseFollowUpAnswer(
  hubText: string,
): { site: string; hasEvidence: boolean; answer: string } | null {
  const m = hubText.match(/^(hospital_\d+)(\s\[no evidence\])?:\s(.+)$/);
  return m ? { site: m[1], hasEvidence: !m[2], answer: m[3] } : null;
}

export type PanelVerdict = {
  status: "survivor" | "killed" | "unverified";
  disease: string;
  refuted: number;
  votes: number;
};

export function parsePanelVerdict(panelText: string): PanelVerdict | null {
  const m = panelText.match(/^(survivor|killed|unverified)\s+(\S+)\s+\((\d+)\/(\d+) refuted\)$/);
  if (!m) return null;
  return {
    status: m[1] as PanelVerdict["status"],
    disease: m[2],
    refuted: Number(m[3]),
    votes: Number(m[4]),
  };
}

export function parseCalibration(
  panelText: string,
): { passed: boolean; disease: string; refuted: number; votes: number } | null {
  const m = panelText.match(
    /^calibration probe (caught|MISSED): planted (\S+) (\d+)\/(\d+) refuted$/,
  );
  if (!m) return null;
  return { passed: m[1] === "caught", disease: m[2], refuted: Number(m[3]), votes: Number(m[4]) };
}

export function parseLensRaised(panelText: string): boolean {
  return /^lens \S+ raised \d+ candidate\(s\)$/.test(panelText);
}
