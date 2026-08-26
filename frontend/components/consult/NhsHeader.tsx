export function NhsHeader() {
  return (
    <>
      <header className="bg-nhs-blue text-white">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-4 px-5 py-3.5">
          <span className="bg-white px-[9px] py-[5px] font-sans text-[20px] font-bold leading-none tracking-[0.06em] text-nhs-blue">
            NHS
          </span>
          <div className="text-[18px] font-semibold">
            Rare Disease Consult Network
            <span className="mt-0.5 block text-[13px] font-normal tracking-[0.02em] opacity-85">
              Ask fifty hospitals. Move no records.
            </span>
          </div>
          <div className="ml-auto text-right text-[13px] leading-snug opacity-90">
            Dr A. Osei · Respiratory
            <br />
            Royal Infirmary
          </div>
        </div>
      </header>
      <div className="h-1 bg-nhs-dark" />
    </>
  );
}
