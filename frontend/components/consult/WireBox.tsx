import type { WireItem } from "@/lib/consultScript";

type WireBoxProps = {
  sent: WireItem[];
  held: string[];
};

export function WireBox({ sent, held }: WireBoxProps) {
  return (
    <details className="group mt-3 border border-rule">
      <summary className="flex cursor-pointer list-none items-center gap-2 bg-paper px-3 py-2 font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-ink-muted">
        <span className="text-ink-faint transition-transform group-open:rotate-90">▸</span>
        What crossed the wire
      </summary>
      <div className="border-t border-rule p-3 font-mono text-[12px] leading-[1.7]">
        <p className="border-b border-rule pb-1 font-serif text-[10px] font-bold uppercase tracking-[0.1em] text-stay">
          Left the hospital
        </p>
        {sent.map((item) => (
          <div key={item.label} className="text-ink">
            <span className="text-ink-muted">{item.label}:</span>{" "}
            <em className="font-bold not-italic text-stay">{item.value}</em>
          </div>
        ))}
        <p className="mt-3 border-b border-rule pb-1 font-serif text-[10px] font-bold uppercase tracking-[0.1em] text-leave">
          Stayed inside
        </p>
        {held.map((item) => (
          <div key={item} className="text-ink-faint">
            <s className="decoration-leave decoration-2">{item}</s>
          </div>
        ))}
      </div>
    </details>
  );
}
