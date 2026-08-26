type CodeChipProps = {
  id: string;
  label?: string;
  state?: "default" | "accepted" | "rejected" | "leaving";
  onClick?: () => void;
};

const stateClass: Record<NonNullable<CodeChipProps["state"]>, string> = {
  default: "border-rule bg-paper-raised text-ink",
  accepted: "border-stay bg-stay-soft text-stay",
  rejected: "border-rule bg-transparent text-ink-faint line-through",
  leaving: "border-leave bg-leave-soft text-leave",
};

export function CodeChip({
  id,
  label,
  state = "default",
  onClick,
}: CodeChipProps) {
  const className = [
    "inline-flex items-baseline gap-2 border px-2.5 py-1.5 text-left",
    "transition-colors duration-150",
    onClick ? "cursor-pointer hover:border-ink-muted" : "",
    stateClass[state],
  ].join(" ");

  const body = (
    <>
      <span className="font-mono text-[12px] tracking-wide tabular-nums">
        {id}
      </span>
      {label ? (
        <span className="font-serif text-[13px] leading-snug">{label}</span>
      ) : null}
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={className}>
        {body}
      </button>
    );
  }

  return <span className={className}>{body}</span>;
}
