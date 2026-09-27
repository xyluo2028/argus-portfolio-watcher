const usd = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const usd0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 });

export function money(v: number | null | undefined, opts: { signed?: boolean; whole?: boolean } = {}): string {
  if (v == null || Number.isNaN(v)) return "–";
  const s = (opts.whole ? usd0 : usd).format(Math.abs(v));
  const sign = v < 0 ? "−" : opts.signed && v > 0 ? "+" : "";
  return `${sign}$${s}`;
}

/** Share prices: cents always, 4 decimals below $1 (e.g. penny stocks). */
export function price(v: number | null | undefined): string {
  if (v == null) return "–";
  return v < 1 ? v.toFixed(4) : usd.format(v);
}

export function pct(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "–";
  const sign = v < 0 ? "−" : v > 0 ? "+" : "";
  return `${sign}${Math.abs(v).toFixed(digits)}%`;
}

export function big(v: number | null | undefined): string {
  if (v == null) return "–";
  return (v < 0 ? "−" : "") + compact.format(Math.abs(v));
}

export function ratio(v: number | null | undefined, digits = 2): string {
  return v == null ? "–" : v.toFixed(digits);
}

/** CSS class for a signed value; the text always carries the sign too. */
export function tone(v: number | null | undefined): string {
  return v == null || v === 0 ? "" : v > 0 ? "up" : "down";
}

export function nyTime(iso: string, withDate = true): string {
  return new Date(iso).toLocaleString("en-US", {
    timeZone: "America/New_York",
    ...(withDate ? { weekday: "short", month: "short", day: "numeric" } : {}),
    hour: "numeric",
    minute: "2-digit",
  }) + " ET";
}

/** When the market is closed a quote is that session's close, whatever its fetch time. */
export function quoteTime(q: { as_of: string; session_date: string }, session: string): string {
  if (session !== "closed") return nyTime(q.as_of);
  const d = new Date(`${q.session_date}T12:00:00Z`);
  return `close ${d.toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" })}`;
}
