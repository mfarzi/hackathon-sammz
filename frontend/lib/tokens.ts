/**
 * Clinical-instrument design tokens for Ask the network.
 * Surfaces: warm archival paper. Accent reserved for the trust boundary.
 */

export const colors = {
  paper: "var(--color-paper)",
  paperRaised: "var(--color-paper-raised)",
  ink: "var(--color-ink)",
  inkMuted: "var(--color-ink-muted)",
  inkFaint: "var(--color-ink-faint)",
  rule: "var(--color-rule)",
  leave: "var(--color-leave)",
  leaveSoft: "var(--color-leave-soft)",
  stay: "var(--color-stay)",
  staySoft: "var(--color-stay-soft)",
  instrument: "var(--color-instrument)",
  instrumentInk: "var(--color-instrument-ink)",
  instrumentMuted: "var(--color-instrument-muted)",
} as const;

export const fonts = {
  serif: "var(--font-serif)",
  mono: "var(--font-mono)",
} as const;

export type ColorToken = keyof typeof colors;
export type FontToken = keyof typeof fonts;
