type QueryBlockProps = {
  rows: { label: string; value: string }[];
};

export function QueryBlock({ rows }: QueryBlockProps) {
  return (
    <div className="mt-2.5 border border-rule bg-paper px-3 py-2.5 font-mono text-[12.5px] leading-relaxed text-ink">
      {rows.map((r) => (
        <div key={r.label}>
          <b className="text-ink">{r.label}:</b> {r.value}
        </div>
      ))}
    </div>
  );
}
