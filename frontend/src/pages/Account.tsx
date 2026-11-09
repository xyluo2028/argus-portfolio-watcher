import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type AccountInfo, type ApiKeyInfo, type AuthStatus, type NewApiKey } from "../api";
import { NewPasswordFields, passwordReady } from "../components/PasswordFields";

const day = (iso: string | null) => (iso ? iso.slice(0, 10) : "–");
const when = (iso: string | null) => (iso ? iso.slice(0, 16).replace("T", " ") : "never");
const message = (e: unknown) => (e instanceof ApiError ? e.message : String(e));

/** Your account (password, API keys); the owner also manages everyone's. Before any account exists,
 * this is where you make the first one. */
export function Account({ auth }: { auth: AuthStatus }) {
  if (!auth.account) return <FirstAccount />;
  return (
    <div className="stack">
      <MyAccount owner={!!auth.owner} />
      {auth.owner && <AllAccounts me={auth.account.username} />}
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
        Argus has no accounts yet, so anyone who can reach it can use it. Your account becomes the owner: it takes over
        every portfolio, watchlist, alert and note recorded so far, and sign-in turns on for everyone, this machine
        included. Then add accounts for bots or other people below.
      </p>
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

function MyAccount({ owner }: { owner: boolean }) {
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
          {owner && <span className="tag agent">Owner</span>}
          <span className="small muted">signed in with {how} · created {day(data.account.created_at)}</span>
        </div>
        <p className="small muted" style={{ margin: 0 }}>
          Your portfolios, watchlists, alerts, notes and DCF models are yours alone; other accounts see a portfolio only
          when you share it.
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
      <div className="grid-2">
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

type Action = { username: string; kind: "key" | "password" } | null;

function AllAccounts({ me }: { me: string }) {
  const [data, setData] = useState<{ accounts: AccountInfo[]; keys: ApiKeyInfo[] } | null>(null);
  const [made, setMade] = useState<NewApiKey | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const load = useCallback(() => { api.accounts().then(setData, (e) => setError(message(e))); }, []);
  useEffect(load, [load]);
  const run = async (fn: () => Promise<unknown>, done?: string) => {
    setError(null);
    setNotice(null);
    try {
      await fn();
      if (done) setNotice(done);
      load();
      return true;
    } catch (e) {
      setError(message(e));
      return false;
    }
  };
  if (!data) return error ? <div className="error">{error}</div> : null;
  return (
    <section className="card stack" style={{ gap: 12 }}>
      <h2 style={{ margin: 0 }}>Accounts</h2>
      <p className="small muted" style={{ margin: 0 }}>
        Everyone who can sign in. Each account sees only its own records. A bot is an account too: give it no password
        and an API key. Only you, as the owner, can manage these.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th style={{ textAlign: "left" }}>Username</th><th>Web sign-in</th><th>Keys</th><th>Status</th><th>Created</th><th /></tr>
          </thead>
          <tbody>
            {data.accounts.map((a) => {
              const self = a.username === me;
              return (
                <tr key={a.id} style={{ cursor: "default", opacity: a.disabled ? 0.5 : 1 }}>
                  <td style={{ textAlign: "left" }}><strong>{a.username}</strong>{self && <span className="muted"> (you)</span>}</td>
                  <td>{a.has_password ? "password" : "keys only"}</td>
                  <td>{a.keys ?? 0}</td>
                  <td>{a.disabled ? "disabled" : "active"}</td>
                  <td>{day(a.created_at)}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn ghost" onClick={() => setAction({ username: a.username, kind: "key" })}>New key</button>
                    {!self && <button className="btn ghost" onClick={() => setAction({ username: a.username, kind: "password" })}>
                      {a.has_password ? "Reset password" : "Set password"}</button>}
                    {!self && <button className="btn ghost" onClick={() => {
                      if (!a.disabled && !window.confirm(`Disable ${a.username}? Its sign-ins and keys stop working until you enable it.`)) return;
                      run(() => api.setAccountDisabled(a.username, !a.disabled));
                    }}>{a.disabled ? "Enable" : "Disable"}</button>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {action?.kind === "key" && (
        <div className="stack" style={{ gap: 8 }}>
          <KeyForm label={`New key for ${action.username}`} onCreate={async (name, days) => {
            await run(async () => { setMade(await api.createAccountKey(action.username, name, days)); setAction(null); });
          }} />
          <div><button className="btn ghost" onClick={() => setAction(null)}>Cancel</button></div>
        </div>
      )}
      {action?.kind === "password" && <ResetPassword username={action.username} onCancel={() => setAction(null)}
        onSave={(pw) => run(() => api.resetPassword(action.username, pw), `New password set for ${action.username}; their browsers were signed out.`)
          .then((ok) => { if (ok) setAction(null); })} />}
      {made && <NewKey made={made} onClose={() => setMade(null)} />}
      {notice && <div className="preview" style={{ marginTop: 0 }}>{notice}</div>}

      <AddAccount onAdd={(username, password) => run(() => api.createAccount(username, password),
        `Created ${username}.${password ? "" : " Make it a key with New key."}`)} />

      <h2 style={{ margin: "8px 0 0" }}>Everyone's API keys</h2>
      <KeyTable keys={data.keys} showAccount onRevoke={(k) => {
        if (!window.confirm(`Revoke ${k.username}'s key "${k.name}"? Whatever uses it stops working at once.`)) return;
        run(() => api.revokeAnyKey(k.id));
      }} />
      {error && <div className="error">{error}</div>}
    </section>
  );
}

function ResetPassword({ username, onSave, onCancel }: { username: string; onSave: (pw: string) => void; onCancel: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  return (
    <form className="stack" style={{ gap: 8 }} onSubmit={(e) => { e.preventDefault(); onSave(password); }}>
      <div className="grid-2">
        <NewPasswordFields label={`New password for ${username}`} password={password} confirm={confirm}
                           onPassword={setPassword} onConfirm={setConfirm} />
      </div>
      <div className="row">
        <button className="btn primary" disabled={!passwordReady(password, confirm)}>Set password</button>
        <button type="button" className="btn ghost" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}

function AddAccount({ onAdd }: { onAdd: (username: string, password: string | null) => Promise<boolean> }) {
  const [username, setUsername] = useState("");
  const [withPassword, setWithPassword] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const ready = username.trim() !== "" && (!withPassword || passwordReady(password, confirm));
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    if (await onAdd(username.trim(), withPassword ? password : null)) {
      setUsername(""); setPassword(""); setConfirm("");
    }
    setBusy(false);
  };
  return (
    <form className="stack" style={{ gap: 8, borderTop: "1px solid var(--border)", paddingTop: 12 }} onSubmit={submit}>
      <h2 style={{ margin: 0 }}>Add an account</h2>
      <div className="grid-2">
        <label className="field">Username
          <input className="input" autoCapitalize="none" spellCheck={false} placeholder="e.g. trader-bot" autoComplete="off"
                 value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="row small" style={{ alignSelf: "end", minHeight: 30 }}>
          <input type="checkbox" checked={withPassword} onChange={(e) => setWithPassword(e.target.checked)} />
          Can sign in to the web UI (needs a password)
        </label>
        {withPassword && <NewPasswordFields password={password} confirm={confirm} onPassword={setPassword} onConfirm={setConfirm} />}
      </div>
      <p className="small muted" style={{ margin: 0 }}>Without a password it signs in with API keys only, which suits a bot.</p>
      <div className="row"><button className="btn primary" disabled={busy || !ready}>Add account</button></div>
    </form>
  );
}
