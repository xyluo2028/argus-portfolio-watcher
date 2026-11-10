import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { ApiError, api, type AccountInfo, type ApiKeyInfo, type AuthStatus, type NewApiKey, type PortfolioRef } from "../api";
import { NewPasswordFields, passwordReady } from "../components/PasswordFields";

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "–");
const when = (iso: string | null) => (iso ? iso.slice(0, 16).replace("T", " ") : "never");
const message = (e: unknown) => (e instanceof ApiError ? e.message : String(e));

/** Your account: password, API keys, sharing. Every account is the same kind and manages only itself;
 * others are created on the sign-in page. Before any account exists, this is where the first one is made. */
export function Account({ auth }: { auth: AuthStatus }) {
  if (!auth.account) return <FirstAccount />;
  return (
    <div className="stack">
      <MyAccount />
      <Sharing me={auth.account.username} />
    </div>
  );
}

function FirstAccount() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.setup({ username: username.trim(), password });
      window.location.assign("/account");
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="card stack" style={{ gap: 12, maxWidth: 520 }} onSubmit={submit}>
      <h2 style={{ margin: 0 }}>Create your account</h2>
      <p style={{ margin: 0 }}>
        Argus has no accounts yet. This first account takes over every portfolio, watchlist, alert and note recorded
        so far. Sign-in then turns on for everyone, this machine included.
      </p>
      <div className="warn-box small">
        Make it <strong>your</strong> account, not a bot's. After that, anyone (a bot too) creates their own account on
        the sign-in page; those start empty, with nothing of yours.
      </div>
      <label className="field">Username
        <input className="input" autoComplete="username" autoCapitalize="none" spellCheck={false}
               value={username} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <NewPasswordFields password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} />
      {error && <div className="error">{error}</div>}
      <div className="row">
        <button className="btn primary" disabled={busy || !username.trim() || !passwordReady(password, confirm)}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </div>
    </form>
  );
}

function NewKey({ made, onClose }: { made: NewApiKey; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const copy = () => navigator.clipboard?.writeText(made.key).then(() => setCopied(true), () => undefined);
  return (
    <div className="preview stack" style={{ gap: 8 }}>
      <div>New key <strong>{made.name}</strong>{made.username ? <> for <strong>{made.username}</strong></> : null}.
        Copy it now; it can't be shown again.</div>
      <code style={{ wordBreak: "break-all", userSelect: "all" }}>{made.key}</code>
      <div className="small muted">Send it as <code>Authorization: Bearer &lt;key&gt;</code> (API, or HTTP MCP with
        {" "}<code>--header</code>).</div>
      <div className="row">
        <button type="button" className="btn" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
        <button type="button" className="btn ghost" onClick={onClose}>Done</button>
      </div>
    </div>
  );
}

function KeyTable({ keys, showAccount, onRevoke }: { keys: ApiKeyInfo[]; showAccount?: boolean; onRevoke: (k: ApiKeyInfo) => void }) {
  if (!keys.length) return <p className="muted small" style={{ margin: 0 }}>No API keys.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {showAccount && <th style={{ textAlign: "left" }}>Account</th>}
            <th style={{ textAlign: "left" }}>Name</th><th>Starts with</th><th>Created</th><th>Last used</th><th>Expires</th><th />
          </tr>
        </thead>
        <tbody>
          {keys.map((k) => (
            <tr key={k.id} style={{ cursor: "default", opacity: k.active ? 1 : 0.5 }}>
              {showAccount && <td style={{ textAlign: "left" }}>{k.username}</td>}
              <td style={{ textAlign: "left" }}>{k.name}</td>
              <td><code>{k.prefix}…</code></td>
              <td>{day(k.created_at)}</td>
              <td>{when(k.last_used_at)}</td>
              <td>{k.expires_at ? day(k.expires_at) : "never"}{!k.active && !k.revoked_at ? " (expired)" : ""}</td>
              <td><button className="btn ghost" onClick={() => onRevoke(k)}>Revoke</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KeyForm({ onCreate, label = "New key" }: { onCreate: (name: string, days?: number) => Promise<void>; label?: string }) {
  const [name, setName] = useState("");
  const [days, setDays] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await onCreate(name.trim(), days ? Number(days) : undefined);
      setName("");
      setDays("");
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="row" style={{ alignItems: "flex-end" }} onSubmit={submit}>
      <label className="field" style={{ flex: 2 }}>{label}
        <input className="input" placeholder="What will use it, e.g. sim routine" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="field" style={{ flex: 1 }}>Expires after (days)
        <input className="input" type="number" min={1} placeholder="never" value={days} onChange={(e) => setDays(e.target.value)} />
      </label>
      <button className="btn primary" disabled={busy || !name.trim()}>Create key</button>
    </form>
  );
}

function MyAccount() {
  const [data, setData] = useState<{ account: AccountInfo; via: string; keys: ApiKeyInfo[] } | null>(null);
  const [made, setMade] = useState<NewApiKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => { api.account().then(setData, (e) => setError(message(e))); }, []);
  useEffect(load, [load]);
  if (!data) return error ? <div className="error">{error}</div> : <p className="muted">Loading…</p>;
  const viaKey = data.via === "key";
  const how = { session: "your password", token: "the server token", key: "an API key", open: "nothing" }[data.via] ?? data.via;
  return (
    <>
      <section className="card stack" style={{ gap: 8 }}>
        <h2 style={{ margin: 0 }}>Your account</h2>
        <div className="row">
          <strong>{data.account.username}</strong>
          <span className="small muted">signed in with {how} · created {day(data.account.created_at)}</span>
        </div>
        <p className="small muted" style={{ margin: 0 }}>
          Your portfolios, watchlists, alerts, notes and DCF models are yours alone; other accounts see a portfolio only
          when you share it. Another account (for a bot, say) is created on the sign-in page: sign out, then Create an
          account.
        </p>
      </section>
      {!viaKey && data.account.has_password && <ChangePassword />}
      <section className="card stack" style={{ gap: 12 }}>
        <h2 style={{ margin: 0 }}>Your API keys</h2>
        <p className="small muted" style={{ margin: 0 }}>For scripts and MCP clients that act as you. A key can read and write like
          your account, but can't make keys or change your password.</p>
        {made && <NewKey made={made} onClose={() => setMade(null)} />}
        <KeyTable keys={data.keys} onRevoke={async (k) => {
          if (!window.confirm(`Revoke key "${k.name}"? Whatever uses it stops working at once.`)) return;
          try { await api.revokeKey(k.id); load(); } catch (e) { setError(message(e)); }
        }} />
        {viaKey ? <p className="small muted" style={{ margin: 0 }}>Sign in with your password to make or revoke keys.</p>
          : <KeyForm onCreate={async (name, days) => {
              try { setMade(await api.createKey(name, days)); setError(null); load(); } catch (e) { setError(message(e)); }
            }} />}
        {error && <div className="error">{error}</div>}
      </section>
    </>
  );
}

function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.changePassword(current, password);
      setNote({ ok: true, text: "Password changed. Other browsers signed in as you were signed out." });
      setCurrent(""); setPassword(""); setConfirm("");
    } catch (err) {
      setNote({ ok: false, text: message(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="card stack" style={{ gap: 12 }} onSubmit={submit}>
      <h2 style={{ margin: 0 }}>Change password</h2>
      <div className="grid-2" style={{ alignItems: "start" }}>
        <label className="field">Current password
          <input className="input" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />
        </label>
        <div />
        <NewPasswordFields label="New password" password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} />
      </div>
      {note && <div className={note.ok ? "preview" : "error"} style={{ marginTop: 0 }}>{note.text}</div>}
      <div className="row"><button className="btn primary" disabled={busy || !current || !passwordReady(password, confirm)}>Change password</button></div>
    </form>
  );
}

/** Share your portfolios read-only with other accounts, and see what others share with you. */
function Sharing({ me }: { me: string }) {
  const [portfolios, setPortfolios] = useState<PortfolioRef[] | null>(null);
  const [who, setWho] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const { hash } = useLocation();
  const load = useCallback(() => { api.portfolios().then(setPortfolios, (e) => setError(message(e))); }, []);
  useEffect(load, [load]);
  useEffect(() => {  // the dashboard's Share button lands here
    if (portfolios && hash === "#sharing") document.getElementById("sharing")?.scrollIntoView({ block: "start" });
  }, [portfolios, hash]);
  if (!portfolios) return null;
  const own = portfolios.filter((p) => !p.shared);
  const shared = portfolios.filter((p) => p.shared);
  const act = async (fn: () => Promise<unknown>) => {
    setError(null);
    try { await fn(); load(); return true; } catch (e) { setError(message(e)); return false; }
  };
  return (
    <section className="card stack" id="sharing" style={{ gap: 12, scrollMarginTop: 120 }}>
      <h2 style={{ margin: 0 }}>Sharing</h2>
      <p className="small muted" style={{ margin: 0 }}>
        Let another account see one of your portfolios, read-only: its positions, performance and analysis. They can't
        change anything, and it never counts toward their "all portfolios". To watch a bot's portfolio, the bot shares it
        with you ({`argus --as <bot> portfolio share <portfolio> --with ${me}`}, or its share_portfolio MCP tool).
      </p>
      {own.length === 0 ? <p className="muted small" style={{ margin: 0 }}>You have no portfolios yet.</p> : (
        <div className="table-wrap">
          <table>
            <thead><tr><th style={{ textAlign: "left" }}>Your portfolio</th><th style={{ textAlign: "left" }}>Shared with</th><th /></tr></thead>
            <tbody>
              {own.map((p) => (
                <tr key={p.id} style={{ cursor: "default" }}>
                  <td style={{ textAlign: "left" }}><strong>{p.name}</strong></td>
                  <td style={{ textAlign: "left" }}>
                    <div className="row">
                      {(p.shared_with ?? []).length === 0 && <span className="muted small">nobody</span>}
                      {(p.shared_with ?? []).map((u) => (
                        <span key={u} className="chip">{u}
                          <button className="btn ghost" style={{ padding: "0 4px" }} aria-label={`Stop sharing ${p.name} with ${u}`}
                                  onClick={() => act(() => api.unsharePortfolio(p.name, u))}>×</button>
                        </span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <form className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }} onSubmit={async (e) => {
                      e.preventDefault();
                      const u = (who[p.id] ?? "").trim();
                      if (u && await act(() => api.sharePortfolio(p.name, u))) setWho({ ...who, [p.id]: "" });
                    }}>
                      <input className="input" style={{ flex: "0 1 160px", width: 160, minWidth: 0 }} placeholder="username" autoCapitalize="none"
                             spellCheck={false} aria-label={`Share ${p.name} with`} value={who[p.id] ?? ""}
                             onChange={(e) => setWho({ ...who, [p.id]: e.target.value })} />
                      <button className="btn" disabled={!(who[p.id] ?? "").trim()}>Share</button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {shared.length > 0 && (
        <>
          <h2 style={{ margin: "4px 0 0" }}>Shared with you</h2>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {shared.map((p) => <li key={p.id}><strong>{p.name}</strong> <span className="muted">from {p.owner}, read-only</span></li>)}
          </ul>
          <p className="small muted" style={{ margin: 0 }}>Pick them under "Shared with me" in the portfolio menu.</p>
        </>
      )}
      {error && <div className="error">{error}</div>}
    </section>
  );
}
