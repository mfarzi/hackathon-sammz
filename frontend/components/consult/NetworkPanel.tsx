import { SITES } from "@/lib/consultScript";
import { SiteNode, type NodeStatus } from "./SiteNode";

export type NodeState = {
  status: NodeStatus;
  matchLabel?: string;
  matchPct?: number;
};

type NetworkPanelProps = {
  nodeStates: Record<string, NodeState>;
  networkSummary: string;
};

export function NetworkPanel({ nodeStates, networkSummary }: NetworkPanelProps) {
  return (
    <aside aria-label="Hospital network" className="border border-rule bg-paper-raised">
      <header className="flex items-baseline justify-between gap-4 border-b border-rule px-4 py-3">
        <h2 className="font-serif text-[15px] font-normal text-ink">Network</h2>
        <span className="font-mono text-[11.5px] text-ink-muted">{networkSummary}</span>
      </header>
      <div>
        {SITES.map((site) => {
          const state = nodeStates[site.id] ?? { status: "idle" as NodeStatus };
          return (
            <SiteNode
              key={site.id}
              site={site}
              status={state.status}
              matchLabel={state.matchLabel}
              matchPct={state.matchPct}
            />
          );
        })}
      </div>
      <div className="border-t border-rule px-4 py-3.5">
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-faint">
          Nothing identifying leaves a site
        </p>
        <p className="mt-1.5 font-serif text-[13px] leading-relaxed text-ink-muted">
          Sites return a judgement their own agent wrote. Record IDs and note text stay behind
          the boundary. Open <b className="font-semibold text-ink">What crossed the wire</b> on
          any reply to check.
        </p>
      </div>
    </aside>
  );
}
