"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Composer } from "@/components/consult/Composer";
import { LiveLogLine, classifyLine, type LiveLine } from "@/components/consult/LiveLog";

const DEFAULT_CASE =
  "Woman in her twenties, months of worsening tremor and slurred speech, marked change in mood and behaviour noted by family, jaundiced on examination, persistently tired, no fever.";

export default function LivePage() {
  const [caseText, setCaseText] = useState(DEFAULT_CASE);
  const [dryRun, setDryRun] = useState(false);
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<LiveLine[]>([]);
  const keyRef = useRef(0);
  const logRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const reportStartedRef = useRef(false);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [lines]);

  function pushLine(kind: LiveLine["kind"], text: string, tag?: string) {
    keyRef.current += 1;
    const key = keyRef.current;
    setLines((prev) => [...prev, { key, kind, text, tag }]);
  }

  async function run() {
    setLines([]);
    reportStartedRef.current = false;
    setRunning(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await fetch("/api/live-consult", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case: caseText, dryRun }),
        signal: controller.signal,
      });

      if (!res.body) {
        pushLine("error", "No response stream — check the server console.");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n");
        buffer = parts.pop() ?? "";
        for (const raw of parts) {
          const classified = classifyLine(raw, reportStartedRef.current);
          if (classified.kind === "rule") reportStartedRef.current = true;
          keyRef.current += 1;
          // Capture the key now: React can batch several setLines calls from
          // this loop and run their updaters later, by which point the ref
          // would already be at its final value for every one of them.
          const key = keyRef.current;
          setLines((prev) => [...prev, { key, ...classified }]);
        }
      }
      if (buffer) {
        const classified = classifyLine(buffer, reportStartedRef.current);
        keyRef.current += 1;
        const key = keyRef.current;
        setLines((prev) => [...prev, { key, ...classified }]);
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        pushLine("error", `Request failed: ${(err as Error).message}`);
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setRunning(false);
  }

  return (
    <div className="mx-auto max-w-[1000px] px-5 py-6">
      <header className="mb-5 border-b border-rule pb-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-faint">
          Rare Disease Consult Network — live
        </p>
        <h1 className="mt-2 font-serif text-[26px] leading-tight text-ink">
          A real consult, run for real.
        </h1>
        <p className="mt-2 max-w-[62ch] font-serif text-[14px] leading-relaxed text-ink-muted">
          This calls the actual Flower federation — five hospital nodes searching their own
          records, the hub asking a follow-up, and the adversarial panel attacking what comes
          back. Nothing here is scripted.{" "}
          <Link href="/" className="underline decoration-ink-faint underline-offset-2">
            See the walkthrough instead →
          </Link>
        </p>
      </header>

      <Composer
        value={caseText}
        onChange={setCaseText}
        onRun={run}
        onReset={() => setCaseText("")}
        running={running}
        canReset={caseText.length > 0}
        hint={dryRun ? "dry run — retrieval only, no model calls" : "5 hospital nodes · Flower"}
      />

      <div className="mt-3 flex items-center gap-4 border-b border-rule pb-4">
        <label className="flex items-center gap-2 font-mono text-[12px] text-ink-muted">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            disabled={running}
          />
          dry run (no model calls, ~15s)
        </label>
        {running && (
          <button
            onClick={stop}
            className="font-mono text-[12px] uppercase tracking-[0.08em] text-red-700 underline"
          >
            Stop
          </button>
        )}
        {running && (
          <span className="font-mono text-[12px] text-ink-faint">
            running — a full consult takes 60–110s
          </span>
        )}
      </div>

      <div
        ref={logRef}
        className="mt-4 h-[560px] overflow-y-auto border border-rule bg-paper-raised p-4 font-mono text-[12.5px] leading-[1.65]"
      >
        {lines.length === 0 && !running && (
          <p className="text-ink-faint">Output will appear here once you start a consult.</p>
        )}
        {lines.map((line) => (
          <LiveLogLine key={line.key} line={line} />
        ))}
      </div>
    </div>
  );
}
