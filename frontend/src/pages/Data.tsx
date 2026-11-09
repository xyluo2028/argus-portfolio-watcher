import { useEffect, useState } from "react";
import { ApiError, api, type PortfolioDeletion, type PortfolioRef } from "../api";
import { ImportCard } from "../components/ImportCard";

const deletionSummary = (d: PortfolioDeletion) => {
  const c = d.counts;
  const parts = [`${c.transactions} transaction${c.transactions === 1 ? "" : "s"}`,
    `${c.open_positions} open position${c.open_positions === 1 ? "" : "s"}`];
  if (c.targets) parts.push(`${c.targets} target weight${c.targets === 1 ? "" : "s"}`);
  if (c.nav_days) parts.push(`${c.nav_days} days of performance history`);
  return parts.join(", ");
};

/** Danger zone: delete one portfolio for good (the server snapshots everything first). */
function DeletePortfolioCard({ onDeleted }: { onDeleted: () => void }) {
  const [portfolios, setPortfolios] = useState<PortfolioRef[]>([]);
  const [name, setName] = useState("");
  const [preview, setPreview] = useState<PortfolioDeletion | null>(null);
  const [typed, setTyped] = useState("");
  const [done, setDone] = useState<PortfolioDeletion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.portfolios().then(setPortfolios, () => setPortfolios([]));
  useEffect(() => { load(); }, []);

  useEffect(() => {
    setPreview(null);
    setTyped("");
    setError(null);
    if (name) api.deletePortfolio(name, true).then(setPreview, (e: ApiError) => setError(e.message));
  }, [name]);

  const remove = async () => {
    if (!preview || typed !== preview.portfolio.name) return;
    setBusy(true);
    setError(null);
    try {
      setDone(await api.deletePortfolio(preview.portfolio.name, false, typed));
      setName("");
      await load();
      onDeleted();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card danger-zone">
      <h2>Delete a portfolio</h2>
      <p className="danger-text" role="alert" style={{ marginTop: 0 }}>
        Deleting a portfolio permanently removes it with all its transactions, target weights and performance history.
        This can't be undone in the app. Watchlists, notes and alerts are kept.
      </p>
      {portfolios.length === 0 ? <p className="muted" style={{ marginBottom: 0 }}>No portfolios.</p> : (
        <div className="stack" style={{ gap: 10 }}>
          <label className="row small" style={{ gap: 8 }}>
            Portfolio
            <select className="input" value={name} onChange={(e) => { setName(e.target.value); setDone(null); }}>
              <option value="">Choose…</option>
              {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            </select>
          </label>
          {preview && (
            <>
              <p className="danger-text" style={{ margin: 0 }}>
                <strong>{preview.portfolio.name}</strong> will be deleted: {deletionSummary(preview)}.
                A backup snapshot is saved to <code>data/snapshots/</code> first; restore it above to undo.
              </p>
              <label className="small" style={{ display: "grid", gap: 6, maxWidth: 360 }}>
                <span>Type <strong>{preview.portfolio.name}</strong> to confirm</span>
                <input className="input" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off"
                       spellCheck={false} aria-label="Portfolio name to confirm" />
              </label>
              <div className="row">
                <button className="btn danger" disabled={busy || typed !== preview.portfolio.name} onClick={remove}>
                  {busy ? "Deleting…" : `Delete ${preview.portfolio.name}`}
                </button>
                <button className="btn ghost" onClick={() => setName("")}>Cancel</button>
              </div>
            </>
          )}
        </div>
      )}
      {done && (
        <div className="preview">
          Deleted <strong>{done.portfolio.name}</strong> ({deletionSummary(done)}).
          {done.backup && <> Backup: <code>{done.backup}</code>.</>}
        </div>
      )}
      {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
    </section>
  );
}

export function Data({ onPortfoliosChanged }: { onPortfoliosChanged?: () => void }) {
  return (
    <div className="stack">
      <ImportCard />

      <section className="card">
        <h2>Back up and restore</h2>
        <p style={{ marginTop: 0 }}>
          A snapshot is one file with every account's portfolios, transactions (including deleted ones), watchlists,
          notes, alerts, targets and audit log, plus the accounts themselves. Because it holds everyone's records,
          it's made and loaded on the server, not from here:
        </p>
        <pre className="small">{"uv run argus snapshot dump\nuv run argus snapshot load <file> --dry-run"}</pre>
        <p className="small muted" style={{ marginBottom: 0 }}>
          <code>uv run argus backup</code> also copies the database; it runs nightly if you set it up (see the README).
        </p>
      </section>

      <DeletePortfolioCard onDeleted={() => onPortfoliosChanged?.()} />
    </div>
  );
}
