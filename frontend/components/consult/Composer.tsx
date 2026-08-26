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
    <div className="border-t border-nhs-grey-4 bg-nhs-grey-5 px-5 py-[14px]">
      <label htmlFor="case" className="mb-1.5 block text-[13px] font-semibold text-nhs-ink">
        Case description
      </label>
      <textarea
        id="case"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        disabled={running}
        className="min-h-[74px] w-full resize-y border-2 border-nhs-ink bg-white px-[11px] py-[9px] text-[15px] text-nhs-ink outline-none disabled:opacity-70"
      />
      <div className="mt-[11px] flex flex-wrap items-center gap-[11px]">
        <button
          type="button"
          onClick={onRun}
          disabled={running}
          className="border-0 border-b-4 border-[#00401e] bg-nhs-green px-5 py-[11px] text-[16px] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40 enabled:hover:bg-[#00672f]"
        >
          {running ? "Consult running…" : "Start consult"}
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={running || !canReset}
          className="border-2 border-nhs-blue bg-white px-5 py-[9px] text-[16px] font-semibold text-nhs-blue disabled:cursor-not-allowed disabled:opacity-40 enabled:hover:bg-nhs-grey-5"
        >
          Clear
        </button>
        <span className="text-[13px] text-nhs-grey-1">{hint}</span>
      </div>
    </div>
  );
}
