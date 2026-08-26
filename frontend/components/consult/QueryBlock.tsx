type QueryBlockProps = {
  rows: { label: string; value: string }[];
};

export function QueryBlock({ rows }: QueryBlockProps) {
  return (
    <div className="mt-[9px] border border-nhs-grey-4 bg-nhs-grey-5 px-[11px] py-[9px] font-mono text-[13px] leading-relaxed text-nhs-ink">
      {rows.map((r) => (
        <div key={r.label}>
          <b className="text-nhs-dark">{r.label}:</b> {r.value}
        </div>
      ))}
    </div>
  );
}
