import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api, type WatchlistSummary } from "../api";
import { pickWatchlist, rememberWatchlist, savedWatchlist, withDefault } from "../watchlists";

const MAX_NAME = 80; // the server's limit on a watchlist name

/** The stock page's watchlist button. One click adds the symbol to the list you're working on (the one the
 * Watchlist page and the Screener remember). Once it's on a list, the button opens a menu instead: add it to
 * other lists, take it off one, or start a new list. Removing always takes a deliberate second click. */
export function WatchButton({ symbol }: { symbol: string }) {
  const [lists, setLists] = useState<WatchlistSummary[] | null>(null);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const box = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  const current = useRef(symbol);
  current.current = symbol;

  // Which lists hold this symbol; a slow answer for the stock you just left must not land on this one.
  const load = (sym: string) => api.watchlists(sym).then(
    (ls) => { if (current.current === sym) setLists(withDefault(ls)); },
    () => { if (current.current === sym) setLists(withDefault([])); });

  useEffect(() => {
    setLists(null);
    setOpen(false);
    setError(null);
    load(symbol);
  }, [symbol]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    document.addEventListener("pointerdown", onDown);
    window.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("pointerdown", onDown); window.removeEventListener("keydown", onKey); };
  }, [open]);

  const change = async (fn: () => Promise<unknown>) => {
    const sym = symbol;
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load(sym);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't update the watchlist.");
    } finally {
      setBusy(false);
    }
  };
  const add = (name: string) => change(async () => {
    await api.watchAdd([symbol], undefined, name);
    rememberWatchlist(name); // the next one-click add, and the Watchlist page, follow your latest choice
  });
  const remove = (name: string) => change(() => api.watchRemove(symbol, name));

  const on = (lists ?? []).filter((l) => l.contains);
  const target = lists ? pickWatchlist(lists, savedWatchlist()) : null;
  const label = !lists ? "☆ Watchlist" : on.length === 0 ? "☆ Add to watchlist"
    : on.length === 1 ? `★ In ${on[0].name}` : `★ In ${on.length} lists`;

  const create = (e: React.FormEvent) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    add(name).then(() => setNewName(""));
  };

  return (
    <div className="watch" ref={box}>
      <div className="watch-buttons">
        <button ref={button} type="button" className={`btn small ${on.length ? "watching" : ""}`} disabled={!lists || busy}
                title={on.length === 0 && target ? `Add ${symbol} to ${target}` : `Watchlists holding ${symbol}`}
                aria-haspopup={on.length ? "true" : undefined} aria-expanded={on.length ? open : undefined}
                onClick={() => {
                  if (on.length === 0 && target) { setOpen(false); add(target); } else setOpen((o) => !o);
                }}>
          {busy ? "Saving…" : label}
        </button>
        {lists && on.length === 0 && (
          <button type="button" className="btn small" aria-label="Choose a watchlist" aria-haspopup="true"
                  aria-expanded={open} disabled={busy} onClick={() => setOpen((o) => !o)}>▾</button>
        )}
      </div>
      {open && lists && (
        <div className="watch-menu" role="group" aria-label={`Watchlists for ${symbol}`}>
          <div className="small muted">Watchlists for {symbol}</div>
          {lists.map((l) => (
            <div key={l.name} className="watch-row">
              <label>
                <input type="checkbox" checked={!!l.contains} disabled={busy}
                       onChange={() => (l.contains ? remove(l.name) : add(l.name))} />
                <span className="watch-name">{l.name}</span>
                <span className="muted small">{l.count}</span>
              </label>
              <Link className="small" to={`/watchlist?list=${encodeURIComponent(l.name)}`}>open</Link>
            </div>
          ))}
          <form className="row" onSubmit={create}>
            <input className="input" placeholder="New list" aria-label="New watchlist name" maxLength={MAX_NAME}
                   value={newName} onChange={(e) => setNewName(e.target.value)} disabled={busy} />
            <button className="btn small" disabled={busy || !newName.trim()}>Add</button>
          </form>
        </div>
      )}
      {error && <div className="error small" role="alert">{error}</div>}
    </div>
  );
}
