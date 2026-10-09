import { Suspense, lazy, useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { ALL, ApiError, UNAUTHORIZED_EVENT, api, type PortfolioRef } from "./api";
import { LiveBadge } from "./components/LiveBadge";
import { ThemeToggle } from "./components/ThemeToggle";
import { Dashboard } from "./pages/Dashboard";
import { useLive } from "./useLive";

// Every page but the dashboard loads on first visit, so the first screen downloads less.
const Alerts = lazy(() => import("./pages/Alerts").then((m) => ({ default: m.Alerts })));
const Screener = lazy(() => import("./pages/Screener").then((m) => ({ default: m.Screener })));
const Markets = lazy(() => import("./pages/Markets").then((m) => ({ default: m.Markets })));
const Analysis = lazy(() => import("./pages/Analysis").then((m) => ({ default: m.Analysis })));
const Compare = lazy(() => import("./pages/Compare").then((m) => ({ default: m.Compare })));
const Data = lazy(() => import("./pages/Data").then((m) => ({ default: m.Data })));
const Ticker = lazy(() => import("./pages/Ticker").then((m) => ({ default: m.Ticker })));
const Transactions = lazy(() => import("./pages/Transactions").then((m) => ({ default: m.Transactions })));
const Watchlist = lazy(() => import("./pages/Watchlist").then((m) => ({ default: m.Watchlist })));

const KEY = "argus.portfolio";

/** Asks for the server's token first when it has one (ARGUS_TOKEN); otherwise goes straight in. */
export function App() {
  const [auth, setAuth] = useState<"checking" | "needed" | "ok">("checking");
  useEffect(() => {
    api.authStatus().then((s) => setAuth(s.authenticated ? "ok" : "needed"), () => setAuth("ok"));
    const onUnauthorized = () => setAuth("needed");
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);
  if (auth === "checking") return null;
  if (auth === "needed") return <SignIn onDone={() => window.location.reload()} />;
  return <Main />;
}

function SignIn({ onDone }: { onDone: () => void }) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(token);
      onDone();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main style={{ maxWidth: 420, margin: "12vh auto 0", padding: "0 16px" }}>
      <form className="card stack" onSubmit={submit} style={{ gap: 12 }}>
        <div className="brand"><span className="brand-dot" aria-hidden />Argus</div>
        <label className="field">Access token
          <input className="input" type="password" autoComplete="current-password" autoFocus value={token}
                 onChange={(e) => setToken(e.target.value)} />
        </label>
        <p className="small muted" style={{ margin: 0 }}>The <code>ARGUS_TOKEN</code> from the server's <code>.env</code>. You stay signed in on this browser for 90 days.</p>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={busy || !token.trim()}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}

function Main() {
  const [portfolios, setPortfolios] = useState<PortfolioRef[] | null>(null);
  const [current, setCurrent] = useState<string>(() => {
    try {
      return localStorage.getItem(KEY) ?? "";
    } catch {
      return "";
    }
  });

  useEffect(() => {
    api.portfolios().then((ps) => {
      setPortfolios(ps);
      setCurrent((c) => (ps.some((p) => p.name === c) || (c === ALL && ps.length > 1) ? c : ps[0]?.name ?? ""));
    }, () => setPortfolios([]));
  }, []);

  useEffect(() => {
    try {
      if (current) localStorage.setItem(KEY, current);
    } catch {
      /* ignore */
    }
  }, [current]);

  const { data: live, connected } = useLive(current || undefined);

  return (
    <>
      <header className="topbar">
        <div className="brand"><span className="brand-dot" aria-hidden />Argus</div>
        <nav className="nav">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/watchlist">Watchlist</NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
          <NavLink to="/analysis">Analysis</NavLink>
          <NavLink to="/markets">Markets</NavLink>
          <NavLink to="/screener">Screener</NavLink>
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/alerts">Alerts{live?.alerts_fired?.length ? ` · ${live.alerts_fired.length}` : ""}</NavLink>
          <NavLink to="/data">Data</NavLink>
        </nav>
        {portfolios && portfolios.length > 0 && (
          <select value={current} onChange={(e) => setCurrent(e.target.value)} aria-label="Portfolio">
            {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            {portfolios.length > 1 && <option value={ALL}>All portfolios</option>}
          </select>
        )}
        <div className="spacer" />
        <LiveBadge live={live} connected={connected} />
        <ThemeToggle />
      </header>
      <main>
        <Suspense fallback={<p className="muted">Loading…</p>}>
        {portfolios === null ? <p className="muted">Loading…</p>
          : portfolios.length === 0 ? (
            <Routes>
              <Route path="/data" element={<Data />} />
              <Route path="*" element={
                <div className="card">
                  <h2>No portfolios yet</h2>
                  <p><Link to="/data">Import an Investing.com CSV</Link>, or restore a snapshot from another machine on the same page.</p>
                  <p className="small muted">From the terminal: <code>uv run argus import investing data/&lt;name&gt;_Holdings_MMDDYYYY.csv --opening-through YYYY-MM-DD</code></p>
                </div>
              } />
            </Routes>
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard portfolio={current} live={live} />} />
              <Route path="/t/:symbol" element={<Ticker portfolio={current} live={live} />} />
              <Route path="/watchlist" element={<Watchlist live={live} />} />
              <Route path="/transactions" element={<Transactions portfolio={current} />} />
              <Route path="/compare" element={<Compare portfolio={current} />} />
              <Route path="/analysis" element={<Analysis portfolio={current} />} />
              <Route path="/markets" element={<Markets />} />
              <Route path="/screener" element={<Screener />} />
              <Route path="/alerts" element={<Alerts live={live} />} />
              <Route path="/data" element={<Data />} />
            </Routes>
          )}
        </Suspense>
      </main>
    </>
  );
}
