import type { WireItem } from "@/lib/consultScript";

type WireBoxProps = {
  sent: WireItem[];
  held: string[];
};

export function WireBox({ sent, held }: WireBoxProps) {
  return (
    <details className="group mt-[11px] border border-nhs-grey-4">
      <summary className="flex cursor-pointer list-none items-center gap-[7px] bg-nhs-grey-5 px-[11px] py-2 text-[12px] font-semibold text-nhs-ink">
        <span className="text-nhs-blue transition-transform group-open:rotate-90">▸</span>
        What crossed the wire
      </summary>
      <div className="border-t border-nhs-grey-4 p-[11px] font-mono text-[12px] leading-[1.7]">
        <p className="mb-1.5 border-b border-nhs-grey-4 pb-1 text-[10px] font-bold uppercase tracking-[0.1em] text-nhs-green">
          Left the hospital
        </p>
        {sent.map((item) => (
          <div key={item.label} className="text-nhs-ink">
            {item.label}: <em className="font-bold not-italic text-nhs-green">{item.value}</em>
          </div>
        ))}
        <p className="mb-1.5 mt-[13px] border-b border-nhs-grey-4 pb-1 text-[10px] font-bold uppercase tracking-[0.1em] text-nhs-red">
          Stayed inside
        </p>
        {held.map((item) => (
          <div key={item} className="text-nhs-grey-2">
            <s className="decoration-nhs-red decoration-2">{item}</s>
          </div>
        ))}
      </div>
    </details>
  );
}
