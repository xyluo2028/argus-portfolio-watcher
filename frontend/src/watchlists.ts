// Which watchlist the UI is working on. Agents (MCP/CLI) create named lists freely, so the
// Watchlist page and the Screener's "+ watch" share one remembered choice instead of assuming
// the default list.
import type { WatchlistSummary } from "./api";

export const DEFAULT_WATCHLIST = "Watchlist";
const KEY = "argus.watchlist";

export function savedWatchlist(): string | null {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

export function rememberWatchlist(name: string) {
  try { localStorage.setItem(KEY, name); } catch { /* ignore */ }
}

/** Every list the server knows, plus the default one, which only exists once something is added to it. */
export function withDefault(lists: WatchlistSummary[]): WatchlistSummary[] {
  return lists.some((l) => l.name === DEFAULT_WATCHLIST) ? lists : [{ name: DEFAULT_WATCHLIST, count: 0 }, ...lists];
}

/** The wanted list if it exists, else the default when it has items, else the first non-empty list. */
export function pickWatchlist(lists: WatchlistSummary[], wanted: string | null): string {
  if (wanted && lists.some((l) => l.name === wanted)) return wanted;
  const def = lists.find((l) => l.name === DEFAULT_WATCHLIST);
  if (def && def.count > 0) return DEFAULT_WATCHLIST;
  return lists.find((l) => l.count > 0)?.name ?? DEFAULT_WATCHLIST;
}
