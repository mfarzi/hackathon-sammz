import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "leave";

const variants: Record<Variant, string> = {
  primary:
    "bg-ink text-paper-raised hover:bg-ink/90 border border-ink",
  secondary:
    "bg-paper-raised text-ink border border-rule hover:border-ink-muted",
  ghost: "bg-transparent text-ink-muted hover:text-ink border border-transparent",
  leave:
    "bg-leave text-paper-raised hover:bg-leave/90 border border-leave",
};

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[
        "inline-flex items-center justify-center gap-2 px-3.5 py-2",
        "font-mono text-[12px] font-medium tracking-[0.04em] uppercase",
        "transition-colors duration-150 disabled:opacity-40 disabled:pointer-events-none",
        variants[variant],
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </button>
  );
}
