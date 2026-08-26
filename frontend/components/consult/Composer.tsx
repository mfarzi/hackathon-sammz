import { Button } from "@/components/ds";

type ComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onRun: () => void;
  onReset: () => void;
  running: boolean;
  canReset: boolean;
  hint: string;
};

export function Composer({
  value,
  onChange,
  onRun,
  onReset,
  running,
  canReset,
  hint,
}: ComposerProps) {
  return (
    <div className="border-t border-rule bg-paper px-5 py-4">
      <label htmlFor="case" className="block font-mono text-[12px] font-semibold text-ink">
        Case description
      </label>
      <textarea
        id="case"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        disabled={running}
        className="mt-1.5 min-h-[74px] w-full resize-y border-2 border-ink bg-paper-raised px-3 py-2 font-serif text-[15px] text-ink outline-none disabled:opacity-70"
      />
      <div className="mt-2.5 flex flex-wrap items-center gap-3">
        <Button onClick={onRun} disabled={running}>
          {running ? "Consult running…" : "Start consult"}
        </Button>
        <Button variant="secondary" onClick={onReset} disabled={running || !canReset}>
          Clear
        </Button>
        <span className="font-serif text-[13px] text-ink-muted">{hint}</span>
      </div>
    </div>
  );
}
