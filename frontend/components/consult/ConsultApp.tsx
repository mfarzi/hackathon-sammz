"use client";

import { useRef, useState, type ReactNode } from "react";
import { CASE_TEXT, SITES, type SiteId } from "@/lib/consultScript";
import {
  classifyLine,
  isRankedHeader,
  parseFollowUpAnswer,
  parseFollowUpQuestion,
  parseLensRaised,
  parsePanelVerdict,
  parseRankedRow,
  parseSitesOnline,
  parseSiteReplied,
  parseSymptoms,
  type PanelVerdict,
  type RankedRow,
} from "@/lib/liveParse";
import { NhsHeader } from "./NhsHeader";
import { ProgressRail } from "./ProgressRail";
import { NetworkPanel, type NodeState } from "./NetworkPanel";
import { Composer } from "./Composer";
import { ThreadMessage } from "./ThreadMessage";
import { QueryBlock } from "./QueryBlock";

const idleNodes = (): Record<SiteId, NodeState> =>
  Object.fromEntries(SITES.map((s) => [s.id, { status: "idle" as const }])) as Record<
    SiteId,
    NodeState
  >;

// hospital_1..5 (the real backend's site ids) map onto H1..H5 in order - the
// fixture's record counts per site were themselves taken from the real data,
// so this is the same network, just now queried for real.
const HOSPITAL_TO_SITE: Record<string, SiteId> = {
  hospital_1: "H1",
  hospital_2: "H2",
  hospital_3: "H3",
  hospital_4: "H4",
  hospital_5: "H5",
};

export function ConsultApp() {
  const [caseText, setCaseText] = useState(CASE_TEXT);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [stageIndex, setStageIndex] = useState(-1);
  const [calls, setCalls] = useState(0);
  const [networkSummary, setNetworkSummary] = useState("5 sites · idle");
  const [hint, setHint] = useState("5 hospital nodes · Flower federation");
  const [nodeStates, setNodeStates] = useState<Record<SiteId, NodeState>>(idleNodes());
  const [messages, setMessages] = useState<{ key: string; node: ReactNode }[]>([]);
  const keyRef = useRef(0);
  const callsRef = useRef(0);
  const stageRef = useRef(-1);

  function push(node: ReactNode) {
    keyRef.current += 1;
    const key = `m-${keyRef.current}`;
    setMessages((prev) => [...prev, { key, node }]);
  }

  function setNode(id: SiteId, state: NodeState) {
    setNodeStates((prev) => ({ ...prev, [id]: state }));
  }

  function bump(n: number) {
    callsRef.current += n;
    setCalls(callsRef.current);
  }

  function advanceStage(n: number) {
    if (n > stageRef.current) {
      stageRef.current = n;
      setStageIndex(n);
    }
  }

  async function run() {
    const text = caseText.trim();
    if (!text) return;

    setRunning(true);
    setFinished(false);
    setMessages([]);
    setCalls(0);
    callsRef.current = 0;
    stageRef.current = -1;
    setNodeStates(idleNodes());
    setNetworkSummary("5 sites · querying");
    setHint("running — a full consult takes 60–110s");

    advanceStage(0);
    push(
      <ThreadMessage who="You" role="clinician">
        <p>{text}</p>
      </ThreadMessage>,
    );
    push(
      <ThreadMessage who="Hub agent" role="hub">
        <p>Consulting the network…</p>
      </ThreadMessage>,
    );

    let rankedRows: RankedRow[] = [];
    let collectingRanked = false;
    let reportStarted = false;
    let queryPushed = false;
    let sawError = false;
    const verdicts: PanelVerdict[] = [];

    function flushRanked() {
      if (!collectingRanked) return;
      collectingRanked = false;
      if (rankedRows.length === 0) return;
      advanceStage(2);
      const totalCases = rankedRows.reduce((sum, r) => sum + r.cases, 0);
      setNetworkSummary(`5 sites · ${totalCases} case${totalCases === 1 ? "" : "s"} pooled`);
      push(
        <ThreadMessage who="Hub agent" role="hub">
          <p>Ranked network-wide by best-match similarity, not case count:</p>
          <div className="mt-2 space-y-1 font-mono text-[12px] text-nhs-grey-1">
            {rankedRows.slice(0, 3).map((r) => (
              <div key={r.disease} className="flex flex-wrap gap-x-3">
                <span className="w-full text-nhs-ink sm:w-[220px] sm:shrink-0">{r.disease}</span>
                <span className="w-[64px] shrink-0">{Math.round(r.score * 100)}%</span>
                <span className="truncate">
                  {r.cases} case{r.cases === 1 ? "" : "s"} · {r.sites.length} site
                  {r.sites.length === 1 ? "" : "s"}
                </span>
              </div>
            ))}
          </div>
        </ThreadMessage>,
      );
    }

    function handleLine(raw: string) {
      const c = classifyLine(raw, reportStarted);

      if (c.kind === "rule") {
        reportStarted = true;
        flushRanked();
        return;
      }
      if (c.kind === "report") return; // superseded by the plain-language summary below
      if (c.kind === "error") {
        sawError = true;
        push(
          <ThreadMessage who="System" role="site-nodata">
            <p>{c.text}</p>
          </ThreadMessage>,
        );
        return;
      }

      if (c.kind === "hub") {
        if (isRankedHeader(c.text)) {
          collectingRanked = true;
          rankedRows = [];
          return;
        }
        if (collectingRanked) {
          const row = parseRankedRow(c.text);
          if (row) {
            rankedRows.push(row);
            return;
          }
          flushRanked();
          // fall through - this line is something else, handle it below
        }

        const sitesOnline = parseSitesOnline(c.text);
        if (sitesOnline != null) {
          advanceStage(1);
          SITES.forEach((s) => setNode(s.id, { status: "searching" }));
          return;
        }

        const symptoms = parseSymptoms(c.text);
        if (symptoms && !queryPushed) {
          queryPushed = true;
          bump(1);
          push(
            <ThreadMessage who="Hub agent" role="hub">
              <p>Parsed into a structured query. No identifiers built, none needed.</p>
              <QueryBlock rows={[{ label: "symptoms", value: symptoms.join(" · ") }]} />
            </ThreadMessage>,
          );
          return;
        }

        const followUp = parseFollowUpQuestion(c.text);
        if (followUp) {
          advanceStage(3);
          bump(1);
          push(
            <ThreadMessage who="Hub agent" role="hub">
              <p>One follow-up question, to narrow the field:</p>
              <QueryBlock rows={[{ label: "asking", value: followUp.question }]} />
            </ThreadMessage>,
          );
          return;
        }

        const answer = parseFollowUpAnswer(c.text);
        if (answer) {
          bump(1);
          const siteId = HOSPITAL_TO_SITE[answer.site];
          const name = SITES.find((s) => s.id === siteId)?.name ?? answer.site;
          push(
            <ThreadMessage
              who={`${name} · follow-up`}
              role={answer.hasEvidence ? "site" : "site-nodata"}
            >
              <p>{answer.answer}</p>
            </ThreadMessage>,
          );
          return;
        }

        // Other hub lines ("N site(s) had comparable cases…", "consult
        // finished in Xs") are already conveyed by what's rendered above.
        return;
      }

      if (c.kind === "site") {
        const reply = parseSiteReplied(c.text);
        if (!reply) return; // "agent read notes…" etc: flavour, not new information
        const siteId = HOSPITAL_TO_SITE[c.tag ?? ""];
        if (!siteId) return;
        bump(1);
        const site = SITES.find((s) => s.id === siteId)!;
        const hasData = reply.matched > 0;
        setNode(siteId, {
          status: hasData ? "answered" : "no-data",
          matchLabel: hasData
            ? `${reply.matched} disease${reply.matched === 1 ? "" : "s"} matched`
            : "No comparable cases",
          matchPct: hasData ? Math.min(100, (reply.matched / 6) * 100) : 0,
        });
        push(
          <ThreadMessage who={site.name} role={hasData ? "site" : "site-nodata"}>
            <p>
              {hasData
                ? `${reply.matched} comparable disease${reply.matched === 1 ? "" : "s"} found.`
                : "No comparable cases."}
            </p>
          </ThreadMessage>,
        );
        return;
      }

      if (c.kind === "panel") {
        if (parseLensRaised(c.text)) {
          advanceStage(4);
          bump(1);
          return;
        }
        const verdict = parsePanelVerdict(c.text);
        if (verdict) {
          bump(1);
          verdicts.push(verdict);
          return; // shown together, plainly, in the final summary
        }
        // Everything else at this stage is internal process detail. Skip.
        return;
      }
    }

    try {
      const res = await fetch("/api/live-consult", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case: text }),
      });
      if (!res.body) throw new Error("No response stream from the server.");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n");
        buffer = parts.pop() ?? "";
        for (const raw of parts) handleLine(raw);
      }
      if (buffer) handleLine(buffer);
      flushRanked();

      if (!sawError) {
        advanceStage(5);
        const confirmed = verdicts.filter((v) => v.status === "survivor");
        push(
          <ThreadMessage who="Result" role="hub">
            {confirmed.length > 0 ? (
              <>
                <p>Worth considering, after independent review by five reviewers:</p>
                {confirmed.map((v) => {
                  const row = rankedRows.find((r) => r.disease === v.disease);
                  return (
                    <p key={v.disease}>
                      <strong className="font-semibold">{v.disease}</strong>
                      {row ? ` — ${row.cases} case${row.cases === 1 ? "" : "s"} across ${row.sites.length} site${row.sites.length === 1 ? "" : "s"}` : ""}
                    </p>
                  );
                })}
                <p className="text-nhs-grey-1">A lead to investigate, not a confirmed diagnosis.</p>
              </>
            ) : (
              <p>Nothing held up on independent review this run.</p>
            )}
          </ThreadMessage>,
        );
      }

      setHint(`${callsRef.current} model calls`);
    } catch (err) {
      push(
        <ThreadMessage who="System" role="site-nodata">
          <p>Request failed: {(err as Error).message}</p>
        </ThreadMessage>,
      );
      setHint("request failed");
    } finally {
      setRunning(false);
      setFinished(true);
    }
  }

  function reset() {
    setMessages([]);
    setNodeStates(idleNodes());
    setStageIndex(-1);
    stageRef.current = -1;
    setCalls(0);
    setNetworkSummary("5 sites · idle");
    setHint("5 hospital nodes · Flower federation");
    setFinished(false);
  }

  return (
    <div className="min-h-dvh bg-nhs-grey-5 font-sans text-nhs-ink">
      <NhsHeader />
      <ProgressRail current={stageIndex} />

      <div className="mx-auto grid max-w-[1400px] grid-cols-1 items-start gap-5 p-5 lg:grid-cols-[340px_1fr]">
        <NetworkPanel nodeStates={nodeStates} networkSummary={networkSummary} />

        <main className="border border-nhs-grey-4 bg-white">
          <header className="flex items-baseline gap-2 border-b border-nhs-grey-4 px-4 py-3">
            <h2 className="text-[15px] font-semibold text-nhs-ink">Consult</h2>
            <span className="ml-auto font-mono text-[12px] text-nhs-grey-1">{calls} model calls</span>
          </header>

          <div className="min-h-[400px] px-5 py-[18px]">
            {messages.length === 0 ? (
              <p className="border-l-4 border-nhs-grey-3 pl-[14px] text-[15px] text-nhs-grey-1">
                Describe the presentation in your own words, then start the consult. Every
                hospital in the network will answer from its own records.
              </p>
            ) : (
              messages.map((m) => <div key={m.key}>{m.node}</div>)
            )}
          </div>

          <Composer
            value={caseText}
            onChange={setCaseText}
            onRun={run}
            onReset={reset}
            running={running}
            canReset={finished}
            hint={hint}
          />
        </main>
      </div>
    </div>
  );
}
