type CalibrationBannerProps = {
  passed: boolean;
};

export function CalibrationBanner({ passed }: CalibrationBannerProps) {
  return (
    <div
      className={[
        "mb-[18px] border-4 px-[15px] py-[13px]",
        passed ? "border-nhs-green bg-nhs-green-soft" : "border-nhs-red bg-nhs-red-soft",
      ].join(" ")}
    >
      <b
        className={[
          "mb-1 block text-[11px] uppercase tracking-[0.09em]",
          passed ? "text-nhs-green" : "text-nhs-red",
        ].join(" ")}
      >
        {passed ? "Calibration passed" : "Calibration failed"}
      </b>
      <p className="text-[15px] leading-normal text-nhs-ink">
        {passed
          ? "The planted false diagnosis was rejected 3–0 on this run, so the other verdicts carry weight."
          : "The planted false diagnosis survived refutation. The verdicts below should not be trusted."}
      </p>
    </div>
  );
}
