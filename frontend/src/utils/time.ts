// Small helper used across admin views to render submitted-at times as a
// human-readable relative string. No date-fns dependency — keeps the bundle
// small.

export function relativeTime(iso: string): string {
  const ts = new Date(iso).getTime();
  if (isNaN(ts)) return "—";
  const delta = (Date.now() - ts) / 1000;
  if (delta < 60) return `${Math.max(1, Math.floor(delta))} sec ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)} min ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)} hr ago`;
  return `${Math.floor(delta / 86400)} d ago`;
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
