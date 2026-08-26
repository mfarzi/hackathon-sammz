"use client";

import { useRef, useState, type ReactNode } from "react";
import {
  CASE_TEXT,
  FOLLOW_UP,
  PARSED_QUERY,
  REPLIES,
  SITES,
  type SiteId,
} from "@/lib/consultScript";
import { ProgressRail } from "./ProgressRail";
import { NetworkPanel, type NodeState } from "./NetworkPanel";
import { Composer } from "./Composer";
import { ThreadMessage } from "./ThreadMessage";
import { QueryBlock } from "./QueryBlock";
import { SiteReplyMessage } from "./SiteReplyMessage";
import { FollowUpAnswers } from "./FollowUpMessage";
import { CalibrationBanner } from "./CalibrationBanner";
import { ReportMessage } from "./ReportMessage";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const idleNodes = (): Record<SiteId, NodeState> =>
  Object.fromEntries(SITES.map((s) => [s.id, { status: "idle" as const }])) as Record<
    SiteId,
    NodeState
  >;

const TOTAL_CASES = REPLIES.reduce((sum, r) => sum + r.caseCount, 0);

export function ConsultApp() {
  const [caseText, setCaseText] = useState(CASE_TEXT);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [stageIndex, setStageIndex] = useState(-1);
  const [calls, setCalls] = useState(0);
  const [networkSummary, setNetworkSummary] = useState("5 sites · idle");
  const [hint, setHint] = useState("5 sites connected · SuperGrid");
  const [nodeStates, setNodeStates] = useState<Record<SiteId, NodeState>>(idleNodes());
  const [messages, setMessages] = useState<{ key: string; node: ReactNode }[]>([]);
  const keyRef = useRef(0);
  const callsRef = useRef(0);

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

  async function run() {
    setRunning(true);
    setFinished(false);
    setMessages([]);
    setCalls(0);
    callsRef.current = 0;
    setNodeStates(idleNodes());
    const text = caseText.trim() || "(no description given)";

    // 1 — clinician
    setStageIndex(0);
    push(
      <ThreadMessage who="You · Royal Infirmary" role="clinician">
        <p>{text}</p>
      </ThreadMessage>,
    );
    await wait(700);

    // 1b — parse
    bump(1);
    push(
      <ThreadMessage who="Hub agent" role="hub">
        <p>Parsed into a structured query. No identifiers built, none needed.</p>
        <QueryBlock rows={PARSED_QUERY} />
      </ThreadMessage>,
    );
    await wait(900);
    setNetworkSummary("5 sites · querying");

    // 2 — fan out
    setStageIndex(1);
    push(
      <ThreadMessage who="Hub agent" role="hub">
        <p>Same query sent to all 5 sites at once. Waiting.</p>
      </ThreadMessage>,
    );
    SITES.forEach((s) => setNode(s.id, { status: "searching" }));
    await wait(1100);

    // 3 — replies, staggered
    setStageIndex(2);
    for (const r of REPLIES) {
      await wait(r.delayMs);
      setNode(r.id, {
        status: r.hasData ? "answered" : "no-data",
        matchLabel: r.hasData ? `${r.caseCount} match${r.caseCount > 1 ? "es" : ""} read locally` : "0 matches",
        matchPct: r.matchPct,
      });
      bump(1);
      const site = SITES.find((s) => s.id === r.id)!;
      push(
        <ThreadMessage
          who={`${site.name}${r.hasData ? " · site agent" : ""}`}
          role={r.hasData ? "site" : "site-nodata"}
        >
          <SiteReplyMessage reply={r} />
        </ThreadMessage>,
      );
    }
    setNetworkSummary(`5 sites · ${TOTAL_CASES} cases found`);
    await wait(800);

    // 4 — follow-up
    setStageIndex(3);
    bump(1);
    push(
      <ThreadMessage who="Hub agent · second round" role="hub">
        <p>{FOLLOW_UP.reasoning}</p>
        <p>Asking the three sites that hold cases:</p>
        <QueryBlock rows={[{ label: "follow-up", value: FOLLOW_UP.question }]} />
      </ThreadMessage>,
    );
    FOLLOW_UP.targets.forEach((id) => setNode(id, { status: "follow-up" }));
    await wait(1200);
    bump(3);
    push(
      <ThreadMessage who="3 sites · answered from own records" role="site">
        <FollowUpAnswers />
      </ThreadMessage>,
    );
    FOLLOW_UP.targets.forEach((id) => setNode(id, { status: "answered" }));
    await wait(900);

    // 5 — panel
    setStageIndex(4);
    bump(20);
    push(
      <ThreadMessage who="Review panel · 5 blind lenses" role="sys">
        <p>
          Four candidates went to refutation. Each was attacked by three reviewers who did not
          raise it. Reviewers reject when uncertain, so surviving means withstanding a real
          attempt to break it.
        </p>
      </ThreadMessage>,
    );
    await wait(1100);

    // 6 — report
    setStageIndex(5);
    push(<CalibrationBanner passed />);
    push(
      <ThreadMessage who="Report · returned to you" role="hub">
        <ReportMessage />
      </ThreadMessage>,
    );

    setHint(`${callsRef.current} model calls · 2 round-trips · 41s`);
    setRunning(false);
    setFinished(true);
  }

  function reset() {
    setMessages([]);
    setNodeStates(idleNodes());
    setStageIndex(-1);
    setCalls(0);
    setNetworkSummary("5 sites · idle");
    setHint("5 sites connected · SuperGrid");
    setFinished(false);
  }

  return (
    <div className="mx-auto max-w-[1400px] px-5 py-6">
      <header className="mb-5 border-b border-rule pb-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          Rare Disease Consult Network
        </p>
        <h1 className="mt-2 font-serif text-[26px] leading-tight text-ink">
          Ask fifty hospitals. Move no records.
        </h1>
      </header>

      <div className="mb-5">
        <ProgressRail current={stageIndex} />
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[340px_1fr]">
        <NetworkPanel nodeStates={nodeStates} networkSummary={networkSummary} />

        <main className="border border-rule bg-paper-raised">
          <header className="flex items-baseline justify-between gap-4 border-b border-rule px-4 py-3">
            <h2 className="font-serif text-[15px] font-normal text-ink">Consult</h2>
            <span className="font-mono text-[11.5px] text-ink-muted">{calls} model calls</span>
          </header>

          <div className="min-h-[400px] px-5 py-5">
            {messages.length === 0 ? (
              <p className="border-l-4 border-ink-faint pl-3.5 font-serif text-[15px] text-ink-muted">
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
