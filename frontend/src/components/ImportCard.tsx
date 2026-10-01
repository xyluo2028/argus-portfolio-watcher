import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, api, type ImportReport } from "../api";

const errText = (e: unknown) => {
  const err = e as ApiError;
  return `${err.message}${err.hint ? ` — ${err.hint}` : ""}`;
};

/** Import an Investing.com holdings CSV: preview (dry run) as settings change, then import. */
export function ImportCard() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<{ name: string; content: string } | null>(null);
  const [portfolio, setPortfolio] = useState("");
  const [cutoff, setCutoff] = useState("");
  const [report, setReport] = useState<ImportReport | null>(null);
  const [done, setDone] = useState<ImportReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const seq = useRef(0);

  const pick = async (f: File | undefined) => {
    setReport(null);
    setDone(null);
    setError(null);
    setPortfolio("");
    setCutoff("");
    setFile(f ? { name: f.name, content: await f.text() } : null);
  };

  // Re-run the dry run whenever the file, name or cutoff changes (debounced; newest answer wins).
  useEffect(() => {
    if (!file) return;
    const n = ++seq.current;
    const t = setTimeout(() => {
      api.importInvesting({ filename: file.name, content: file.content, portfolio: portfolio.trim() || undefined,
                            opening_through: cutoff || undefined, dry_run: true }).then((r) => {
        if (n !== seq.current) return;
        setReport(r);
        setError(null);
        if (!portfolio && r.portfolio) setPortfolio(r.portfolio); // name from the file name
      }, (e) => n === seq.current && (setReport(null), setError(errText(e))));
    }, 300);
    return () => clearTimeout(t);
  }, [file, portfolio, cutoff]);

  // Lots per open date, to help pick the cutoff: a cluster of early dates is usually the existing holdings.
  const dates = useMemo(() => {
    const m = new Map<string, number>();
    for (const l of report?.lot_preview ?? []) m.set(l.date, (m.get(l.date) ?? 0) + 1);
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [report]);

  const runImport = async () => {
    if (!file || !report) return;
    setBusy(true);
    setError(null);
    try {
      setDone(await api.importInvesting({ filename: file.name, content: file.content, portfolio: portfolio.trim(),
                                          opening_through: cutoff || undefined, dry_run: false }));
      setReport(null);
      setFile(null);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  };

  const ready = report?.status === "ok" && !!portfolio.trim();
  return (
    <section className="card">
      <h2>Import from Investing.com</h2>
      <p style={{ marginTop: 0 }}>
        Export your holdings (Portfolio → Holdings → Export) and choose the CSV. You'll see a preview before anything is saved;
        importing the same file again skips lots already recorded.
      </p>
      <div className="row">
        <input ref={fileInput} type="file" accept=".csv,text/csv" hidden
               onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
        <button className="btn" onClick={() => fileInput.current?.click()}>Choose CSV…</button>
        {file && <span className="small muted">{file.name}</span>}
      </div>

      {file && report && (
        <div className="stack" style={{ marginTop: 12, gap: 12 }}>
          <div className="row">
            <label className="field">Portfolio
              <input className="input" value={portfolio} onChange={(e) => setPortfolio(e.target.value)} placeholder="e.g. growth" />
            </label>
            <label className="field">Already owned through (optional)
              <input className="input" type="date" value={cutoff} onChange={(e) => setCutoff(e.target.value)} />
            </label>
          </div>
          <p className="small muted" style={{ margin: 0 }}>
            Lots opened on or before that date are recorded as holdings you already had (Opening); later ones as buys.
            {!cutoff && " With no date, every lot is a buy on its open date."}
          </p>

          {dates.length > 1 && (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Open date</th><th>Lots</th><th aria-label="Use as cutoff" /></tr></thead>
                <tbody>
                  {dates.map(([d, n]) => (
                    <tr key={d} style={{ cursor: "default" }} className={cutoff && d <= cutoff ? "muted" : undefined}>
                      <td>{d}</td><td>{n}</td>
                      <td style={{ textAlign: "right" }}>
                        <button className="btn ghost" onClick={() => setCutoff(d)} aria-pressed={cutoff === d}>
                          {cutoff === d ? "Cutoff ✓" : "Owned through here"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="preview" style={{ marginTop: 0 }}>
            <strong>{report.lots} lots, {report.symbols} symbols</strong>: {report.by_type.OPENING} opening, {report.by_type.BUY} buys
            {" · "}{report.creates_portfolio ? `creates portfolio “${report.portfolio}”` : `adds to “${report.portfolio}”`}
            {!!report.skipped_existing && ` · ${report.skipped_existing} already imported, skipped`}
            <ul style={{ margin: "8px 0 0", paddingLeft: 18 }}>
              {report.checks.map((c) => (
                <li key={c.check} className={c.ok ? undefined : "down"}>{c.ok ? "✓" : "✗"} {c.detail}</li>
              ))}
            </ul>
          </div>

          <div className="row">
            <button className="btn primary" disabled={!ready || busy} onClick={runImport}>
              {busy ? "Importing…" : `Import ${report.lots - (report.skipped_existing ?? 0)} lots`}
            </button>
            <button className="btn ghost" onClick={() => pick(undefined)}>Cancel</button>
            {report.status === "blocked" && <span className="small down">Fix the failed checks first.</span>}
          </div>
        </div>
      )}
      {file && !report && !error && <p className="muted">Checking the file…</p>}

      {done && (
        <div className="preview">
          Imported {done.inserted} lots into “{done.portfolio}”{done.skipped_existing ? ` (${done.skipped_existing} already there)` : ""}.
          {" "}<button className="btn primary" onClick={() => window.location.assign("/")}>Open dashboard</button>
        </div>
      )}
      {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
    </section>
  );
}
