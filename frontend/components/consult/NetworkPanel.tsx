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
    <aside aria-label="Hospital network" className="border border-nhs-grey-4 bg-white">
      <header className="flex items-baseline gap-2 border-b border-nhs-grey-4 px-4 py-3">
        <h2 className="text-[15px] font-semibold text-nhs-ink">Network</h2>
        <span className="ml-auto font-mono text-[12px] text-nhs-grey-1">{networkSummary}</span>
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
      <header className="border-t border-nhs-grey-4 px-4 py-3">
        <h2 className="text-[13px] font-semibold text-nhs-ink">Nothing identifying leaves a site</h2>
      </header>
      <div className="px-4 pb-4 text-[13px] leading-normal text-nhs-grey-1">
        Sites return a judgement their own agent wrote. Record IDs and note text stay behind
        the boundary. Open <b className="font-semibold text-nhs-ink">What crossed the wire</b> on
        any reply to check.
      </div>
    </aside>
  );
}
