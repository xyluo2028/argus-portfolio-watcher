import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, type Quote, type StreamUpdate, type WatchItem } from "../api";
import { HoldingsTabs, PickCell, type Selection } from "../components/HoldingsTabs";
import { TickerInput } from "../components/TickerInput";
import { big, extLabel, pct, price, ratio, tone } from "../format";

const pctCell = (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(1)}%`);

type Live = { i: WatchItem; q: Quote | null };
const COLS: { key: string; label: string; value: (r: Live) => number | string | null | undefined }[] = [
  { key: "symbol", label: "Symbol", value: (r) => r.i.symbol },
  { key: "price", label: "Price", value: (r) => r.q?.price },
  { key: "change_pct", label: "Day %", value: (r) => r.q?.change_pct },
  { key: "market_cap", label: "Mkt cap", value: (r) => r.i.metrics?.market_cap },
  { key: "pe_ttm", label: "P/E", value: (r) => r.i.metrics?.pe_ttm },
  { key: "pe_forward", label: "Fwd P/E", value: (r) => r.i.metrics?.pe_forward },
  { key: "ps_ttm", label: "P/S", value: (r) => r.i.metrics?.ps_ttm },
  { key: "revenue_growth_yoy_pct", label: "Rev growth", value: (r) => r.i.metrics?.revenue_growth_yoy_pct },
  { key: "net_margin_pct", label: "Net margin", value: (r) => r.i.metrics?.net_margin_pct },
  { key: "note", label: "Note", value: (r) => r.i.note?.toLowerCase() || null },
];
const SORT_KEY = "argus.watchlist.sort";

/** The watchlist's own tab: click any header to sort (again to reverse); blanks always sort last. */
function WatchTable({ items, live, sel, onRemove }: {
  items: WatchItem[]; live: StreamUpdate | null; sel: Selection; onRemove: (s: string) => void;
}) {
  const navigate = useNavigate();
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(() => {
    try { return JSON.parse(localStorage.getItem(SORT_KEY) ?? "null"); } catch { return null; }
  });
  const pick = (key: string) => {
    const next = sort?.key === key ? { key, dir: (sort.dir * -1) as 1 | -1 } : { key, dir: (key === "symbol" || key === "note" ? 1 : -1) as 1 | -1 };
    setSort(next);
    try { localStorage.setItem(SORT_KEY, JSON.stringify(next)); } catch { /* ignore */ }
  };
  const rows = useMemo(() => {
    const list: Live[] = items.map((i) => ({ i, q: live?.quotes[i.symbol] ?? i.quote }));
    const col = sort && COLS.find((c) => c.key === sort.key);
    if (!sort || !col) return list; // the order you added them
    return [...list].sort((a, b) => {
      const x = col.value(a), y = col.value(b);
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
    });
  }, [items, live, sort]);

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th className="pick" aria-label="Select to compare" />
            <th className="rank" title="Rank in the current sort order">#</th>
            {COLS.map((c) => (
              <th key={c.key} onClick={() => pick(c.key)} className={c.key === "symbol" || c.key === "note" ? "left" : undefined}
                  aria-sort={sort?.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
                {c.label}{sort?.key === c.key ? (sort.dir === 1 ? " ↑" : " ↓") : ""}
              </th>
            ))}
            <th aria-label="Remove" />
          </tr>
        </thead>
        <tbody>
          {rows.map(({ i, q }, n) => {
            const m = i.metrics ?? {};
            return (
              <tr key={i.symbol} onClick={() => navigate(`/t/${i.symbol}`)}>
                <PickCell symbol={i.symbol} sel={sel} />
                <td className="rank">{n + 1}</td>
                <td className="left"><span className="sym">{i.symbol}</span></td>
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
                          onClick={(e) => { e.stopPropagation(); onRemove(i.symbol); }}>×</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {sort && <button className="btn ghost small" style={{ marginTop: 6 }} onClick={() => { setSort(null); try { localStorage.removeItem(SORT_KEY); } catch { /* ignore */ } }}>Back to the order added</button>}
    </div>
  );
}

export function Watchlist({ live }: { live: StreamUpdate | null }) {
  const [items, setItems] = useState<WatchItem[] | null>(null);
  const [input, setInput] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api.watchlist().then((w) => setItems(w.items), (e: ApiError) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    const symbols = input.split(/[\s,]+/).filter(Boolean);
    if (!symbols.length) return;
    setBusy(true);
    setError(null);
    try {
      await api.watchAdd(symbols, note || undefined);
      setInput("");
      setNote("");
      await load();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (symbol: string) => {
    await api.watchRemove(symbol).catch((e: ApiError) => setError(e.message));
    load();
  };

  return (
    <div className="stack">
      <section className="card">
        <h2>Add to watchlist</h2>
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
          <h2>Watchlist</h2>
          <p className="muted">Nothing yet. Add tickers above, or ask Claude: “add TSLA to my Argus watchlist”.</p>
        </section>
      ) : (
        <HoldingsTabs source={{ kind: "watchlist", name: "Watchlist" }}
                      rows={items.map((i) => ({ symbol: i.symbol, name: null, price: (live?.quotes[i.symbol] ?? i.quote)?.price ?? null }))}
                      first={{ label: `Watchlist · ${items.length}`, content: (_rows, sel) => (
                        <WatchTable items={items} live={live} sel={sel} onRemove={remove} />
                      ) }} />
      )}
    </div>
  );
}
