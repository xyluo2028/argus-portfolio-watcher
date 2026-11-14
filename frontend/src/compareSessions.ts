/** Recent comparisons, kept in this browser so a comparison survives leaving the page. */

export interface CompareSession { symbols: string[]; at: number }

const KEY = "argus.compare.sessions";
const MAX = 15;
export const COMPARE_MAX = 10;

export function loadSessions(): CompareSession[] {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((s) => Array.isArray(s?.symbols) && s.symbols.length) : [];
  } catch {
    return [];
  }
}

const same = (a: string[], b: string[]) => a.length === b.length && [...a].sort().join() === [...b].sort().join();

/** Record a comparison as the most recent one; the same set of symbols is kept once. */
export function rememberSession(symbols: string[]): CompareSession[] {
  const next = [{ symbols, at: Date.now() }, ...loadSessions().filter((s) => !same(s.symbols, symbols))].slice(0, MAX);
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode: history just isn't kept */ }
  return next;
}

export function forgetSession(symbols: string[]): CompareSession[] {
  const next = loadSessions().filter((s) => !same(s.symbols, symbols));
  try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* ignore */ }
  return next;
}

export function clearSessions(): void {
  try { localStorage.removeItem(KEY); } catch { /* ignore */ }
}

export const parseSymbols = (s: string | null | undefined) =>
  [...new Set((s ?? "").split(/[\s,]+/).map((x) => x.trim().toUpperCase()).filter(Boolean))];

export const compareUrl = (symbols: string[]) => `/compare?s=${symbols.slice(0, COMPARE_MAX).join(",")}`;

export function ago(t: number): string {
  const m = Math.round((Date.now() - t) / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h ago`;
  const d = Math.round(h / 24);
  return d < 30 ? `${d} d ago` : new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
