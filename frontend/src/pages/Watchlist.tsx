import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ApiError, api, type StreamUpdate, type WatchItem, type WatchlistSummary } from "../api";
import { HoldingsTabs } from "../components/HoldingsTabs";
import { TickerInput } from "../components/TickerInput";
import { big, extLabel, pct, price, ratio, tone } from "../format";
import { DEFAULT_WATCHLIST, pickWatchlist, rememberWatchlist, savedWatchlist, withDefault } from "../watchlists";

const pctCell = (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(1)}%`);

export function Watchlist({ live }: { live: StreamUpdate | null }) {
  const [lists, setLists] = useState<WatchlistSummary[] | null>(null);
  const [items, setItems] = useState<WatchItem[] | null>(null);
  const [input, setInput] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();

  // ?list= wins (shareable), then the remembered choice; a new list typed by the user exists
  // only in the URL until its first ticker is added.
  const wanted = params.get("list");
  const known = lists ? withDefault(lists) : null;
  const options = known && wanted && !known.some((l) => l.name === wanted) ? [...known, { name: wanted, count: 0 }] : known;
  const selected = options ? pickWatchlist(options, wanted ?? savedWatchlist()) : null;

  const select = (name: string) => {
    rememberWatchlist(name);
    setParams(name === DEFAULT_WATCHLIST && !wanted ? {} : { list: name }, { replace: true });
  };
  const newList = () => {
    const name = window.prompt("Name of the new watchlist")?.trim();
    if (name) select(name);
  };

  const loadLists = useCallback(() => api.watchlists().then(setLists, (e: ApiError) => setError(e.message)), []);
  useEffect(() => { loadLists(); }, [loadLists]);

  const current = useRef(selected);
  current.current = selected;
  const load = useCallback(() => {
    if (!selected) return;
    const exists = (lists ?? []).some((l) => l.name === selected);
    if (!exists && selected !== DEFAULT_WATCHLIST) { setItems([]); return; }  // not created yet
    // A slow answer for the list switched away from must not overwrite the new one.
    return api.watchlist(selected).then((w) => current.current === selected && setItems(w.items),
                                        (e: ApiError) => current.current === selected && setError(e.message));
  }, [selected, lists]);
  useEffect(() => { setItems(null); setError(null); }, [selected]);
  useEffect(() => { load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbols = input.split(/[\s,]+/).filter(Boolean);
    if (!symbols.length || !selected) return;
    setBusy(true);
    setError(null);
    try {
      await api.watchAdd(symbols, note || undefined, selected);
      rememberWatchlist(selected);
      setInput("");
      setNote("");
      await loadLists();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (symbol: string) => {
    if (!selected) return;
    await api.watchRemove(symbol, selected).catch((e: ApiError) => setError(e.message));
    loadLists();
  };

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <div className="seg tabs" role="group" aria-label="Watchlists">
            {(options ?? []).map((l) => (
              <button key={l.name} aria-pressed={l.name === selected} onClick={() => select(l.name)}>
                {l.name} <span className="muted">· {l.count}</span>
              </button>
            ))}
          </div>
          <button className="btn ghost small" onClick={newList}>+ New list</button>
        </div>
        <h2>Add to {selected ?? "watchlist"}</h2>
        <form className="row" onSubmit={add}>
          <TickerInput placeholder="Tickers or company, e.g. TSLA, COST" value={input} onChange={setInput}
                       aria-label="Tickers" />
          <input className="input" placeholder="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)}
                 aria-label="Note" style={{ flex: 2 }} />
          <button className="btn primary" disabled={busy}>{busy ? "Adding…" : "Add"}</button>
        </form>
        {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      </section>

      {!items ? <section className="card"><p className="muted">Loading…</p></section> : items.length === 0 ? (
        <section className="card">
          <h2>{selected}</h2>
          <p className="muted">Nothing yet. Add tickers above, or ask Claude: “add TSLA to my Argus watchlist”.</p>
        </section>
      ) : (
        <HoldingsTabs key={selected} source={{ kind: "watchlist", name: selected! }}
                      rows={items.map((i) => ({ symbol: i.symbol, name: null, price: (live?.quotes[i.symbol] ?? i.quote)?.price ?? null }))}
                      first={{ label: `${selected} · ${items.length}`, content: (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Symbol</th><th>Price</th><th>Day %</th><th>Mkt cap</th><th>P/E</th><th>Fwd P/E</th><th>P/S</th>
              <th>Rev growth</th><th>Net margin</th><th>Note</th><th aria-label="Remove" />
            </tr>
          </thead>
          <tbody>
            {items.map((i) => {
              const q = live?.quotes[i.symbol] ?? i.quote;
              const m = i.metrics ?? {};
              return (
                <tr key={i.symbol} onClick={() => navigate(`/t/${i.symbol}`)}>
                  <td><span className="sym">{i.symbol}</span></td>
                  <td>{price(q?.price)}</td>
                  <td className={tone(q?.change_pct)}>
                    {pct(q?.change_pct)}
                    {q?.ext_price != null && (
                      <span className="ext-line" title={`${extLabel(q.ext_session)} ${price(q.ext_price)}`}>
                        {extLabel(q.ext_session, true)} <span className={tone(q.ext_change_pct)}>{pct(q.ext_change_pct)}</span>
                      </span>
                    )}
                  </td>
                  <td>{big(m.market_cap)}</td>
                  <td>{ratio(m.pe_ttm, 1)}</td>
                  <td>{ratio(m.pe_forward, 1)}</td>
                  <td>{ratio(m.ps_ttm, 1)}</td>
                  <td className={tone(m.revenue_growth_yoy_pct)}>{pct(m.revenue_growth_yoy_pct, 1)}</td>
                  <td>{pctCell(m.net_margin_pct)}</td>
                  <td style={{ textAlign: "left", whiteSpace: "normal" }} className="text-2">{i.note ?? ""}</td>
                  <td>
                    <button className="btn ghost" title={`Remove ${i.symbol}`}
                            onClick={(e) => { e.stopPropagation(); remove(i.symbol); }}>×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
                      ) }} />
      )}
    </div>
  );
}
