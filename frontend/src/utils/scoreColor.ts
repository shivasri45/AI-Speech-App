// Shared score → tailwind class mapping. Use everywhere a score badge
// renders so colours stay consistent across the admin UI.

export interface ScoreColorClasses {
  text: string;
  bg: string;
  border: string;
  label: string;
}

export function scoreColorClasses(
  score: number | null | undefined,
): ScoreColorClasses {
  const s = typeof score === "number" ? score : -1;
  if (s >= 85)
    return {
      text: "text-emerald-300",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
      label: "Excellent",
    };
  if (s >= 70)
    return {
      text: "text-brand-300",
      bg: "bg-brand-500/10",
      border: "border-brand-500/30",
      label: "Good",
    };
  if (s >= 50)
    return {
      text: "text-amber-300",
      bg: "bg-amber-500/10",
      border: "border-amber-500/30",
      label: "Practice",
    };
  if (s >= 0)
    return {
      text: "text-rose-300",
      bg: "bg-rose-500/10",
      border: "border-rose-500/30",
      label: "Needs work",
    };
  return {
    text: "text-zinc-500",
    bg: "bg-zinc-900/60",
    border: "border-zinc-800/70",
    label: "—",
  };
}
