type CalibrationBannerProps = {
  passed: boolean;
};

export function CalibrationBanner({ passed }: CalibrationBannerProps) {
  return (
    <div
      className={[
        "mb-5 border-l-4 px-4 py-3.5",
        passed ? "border-stay bg-stay-soft" : "border-leave bg-leave-soft",
      ].join(" ")}
    >
      <p
        className={[
          "font-mono text-[11px] font-bold uppercase tracking-[0.1em]",
          passed ? "text-stay" : "text-leave",
        ].join(" ")}
      >
        {passed ? "Calibration passed" : "Calibration failed"}
      </p>
      <p className="mt-1 font-serif text-[14px] leading-relaxed text-ink">
        {passed
          ? "The planted false diagnosis was rejected 3–0 on this run, so the other verdicts carry weight."
          : "The planted false diagnosis survived refutation. The verdicts below should not be trusted."}
      </p>
    </div>
  );
}
