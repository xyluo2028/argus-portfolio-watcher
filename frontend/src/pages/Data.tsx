import { useRef, useState } from "react";
import { ApiError, api, type RestoreReport } from "../api";
import { ImportCard } from "../components/ImportCard";
import { nyTime } from "../format";

// What a snapshot holds, in the order people care about. Instruments are metadata, so not listed.
const LABELS: [string, string][] = [
  ["portfolio", "portfolios"], ["txn", "transactions"], ["watchlist_item", "watchlist items"], ["note", "notes"],
  ["alert", "alerts"], ["target", "targets"], ["alert_event", "alert history"], ["audit_log", "audit entries"],
];
const summary = (counts: Record<string, number>) =>
  LABELS.filter(([k]) => counts[k]).map(([k, label]) => `${counts[k]} ${label}`).join(", ") || "no records";

export function Data() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [doc, setDoc] = useState<unknown>(null);
  const [fileName, setFileName] = useState("");
  const [preview, setPreview] = useState<RestoreReport | null>(null);
  const [done, setDone] = useState<RestoreReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pick = async (file: File | undefined) => {
    setPreview(null);
    setDone(null);
    setError(null);
    if (!file) return;
    setFileName(file.name);
    try {
      const parsed = JSON.parse(await file.text());
      setDoc(parsed);
      setPreview(await api.restoreSnapshot(parsed, false, true));
    } catch (e) {
      setDoc(null);
      setError(e instanceof ApiError ? e.message : "That file isn't valid JSON.");
    }
  };

  const restore = async () => {
    if (!preview) return;
    const replacing = Object.keys(preview.will_remove).length > 0;
    if (replacing && !window.confirm(`Replace ${summary(preview.will_remove)} with the snapshot? Your current records are backed up first.`)) return;
    setBusy(true);
    setError(null);
    try {
      setDone(await api.restoreSnapshot(doc, replacing, false));
      setPreview(null);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  };

  const replacing = preview && Object.keys(preview.will_remove).length > 0;
  return (
    <div className="stack">
      <ImportCard />

      <section className="card">
        <h2>Back up</h2>
        <p style={{ marginTop: 0 }}>
          Download one file with your portfolios, transactions (including deleted ones), watchlists, notes, alerts,
          targets and audit log. Market data isn't included; it refills on its own.
        </p>
        <a className="btn primary" href={api.snapshotUrl} download>Download snapshot</a>
      </section>

      <section className="card">
        <h2>Restore</h2>
        <p style={{ marginTop: 0 }}>Load a snapshot file, for example on a new machine. You'll see what it contains before anything changes.</p>
        <div className="row">
          <input ref={fileInput} type="file" accept=".json,application/json" hidden
                 onChange={(e) => { pick(e.target.files?.[0]); e.target.value = ""; }} />
          <button className="btn" onClick={() => fileInput.current?.click()}>Choose file…</button>
          {fileName && <span className="small muted">{fileName}</span>}
        </div>

        {preview && (
          <div className="stack" style={{ marginTop: 12, gap: 10 }}>
            <div className="preview" style={{ marginTop: 0 }}>
              Snapshot{preview.created_at ? ` taken ${nyTime(preview.created_at)}` : ""}: <strong>{summary(preview.counts)}</strong>
            </div>
            {replacing && (
              <div className="warn-box">
                This instance already has {summary(preview.will_remove)}. Restoring replaces them; they're saved to a backup file in
                {" "}<code>data/snapshots/</code> first.
              </div>
            )}
            <div className="row">
              <button className={`btn ${replacing ? "danger" : "primary"}`} disabled={busy} onClick={restore}>
                {busy ? "Restoring…" : replacing ? "Replace my records" : "Restore"}
              </button>
              <button className="btn ghost" onClick={() => { setPreview(null); setFileName(""); }}>Cancel</button>
            </div>
          </div>
        )}

        {done && (
          <div className="preview">
            Restored {summary(done.counts)}.
            {done.backup && <> Previous records saved to <code>{done.backup}</code>.</>}
            {" "}<button className="btn primary" onClick={() => window.location.assign("/")}>Open dashboard</button>
          </div>
        )}
        {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
      </section>
    </div>
  );
}
