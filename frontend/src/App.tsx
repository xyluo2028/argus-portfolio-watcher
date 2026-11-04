import { Suspense, lazy, useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { ALL, ApiError, UNAUTHORIZED_EVENT, api, type AuthStatus, type PortfolioRef, type SignInMethod } from "./api";
import { LiveBadge } from "./components/LiveBadge";
import { ThemeToggle } from "./components/ThemeToggle";
import { TickerSearch } from "./components/TickerSearch";
import { Dashboard } from "./pages/Dashboard";
import { useLive } from "./useLive";

// Every page but the dashboard loads on first visit, so the first screen downloads less.
const Alerts = lazy(() => import("./pages/Alerts").then((m) => ({ default: m.Alerts })));
const Screener = lazy(() => import("./pages/Screener").then((m) => ({ default: m.Screener })));
const Markets = lazy(() => import("./pages/Markets").then((m) => ({ default: m.Markets })));
const Analysis = lazy(() => import("./pages/Analysis").then((m) => ({ default: m.Analysis })));
const Compare = lazy(() => import("./pages/Compare").then((m) => ({ default: m.Compare })));
const Dcf = lazy(() => import("./pages/Dcf").then((m) => ({ default: m.Dcf })));
const Data = lazy(() => import("./pages/Data").then((m) => ({ default: m.Data })));
const Ticker = lazy(() => import("./pages/Ticker").then((m) => ({ default: m.Ticker })));
const Transactions = lazy(() => import("./pages/Transactions").then((m) => ({ default: m.Transactions })));
const Watchlist = lazy(() => import("./pages/Watchlist").then((m) => ({ default: m.Watchlist })));

const KEY = "argus.portfolio";

/** Asks to sign in first when the server wants it (an account exists, or ARGUS_TOKEN is set). */
export function App() {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  useEffect(() => {
    const open: AuthStatus = { required: false, authenticated: true, methods: [], account: null };
    api.authStatus().then(setAuth, () => setAuth(open));
    const onUnauthorized = () => api.authStatus().then(setAuth, () => setAuth({ ...open, authenticated: false, methods: ["password"] }));
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);
  if (auth === null) return null;
  if (!auth.authenticated) return <SignIn methods={auth.methods} onDone={() => window.location.reload()} />;
  return <Main auth={auth} />;
}

function SignIn({ methods, onDone }: { methods: SignInMethod[]; onDone: () => void }) {
  const [method, setMethod] = useState<SignInMethod>(methods.includes("password") ? "password" : "token");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ready = method === "password" ? username.trim() !== "" && password !== "" : token.trim() !== "";
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.login(method === "password" ? { username: username.trim(), password } : { token: token.trim() });
      onDone();
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  };
  const other: SignInMethod = method === "password" ? "token" : "password";
  return (
    <main style={{ maxWidth: 420, margin: "12vh auto 0", padding: "0 16px" }}>
      <form className="card stack" onSubmit={submit} style={{ gap: 12 }}>
        <div className="brand"><span className="brand-dot" aria-hidden />Argus</div>
        {method === "password" ? (
          <>
            <label className="field">Username
              <input className="input" autoComplete="username" autoCapitalize="none" spellCheck={false} autoFocus
                     value={username} onChange={(e) => setUsername(e.target.value)} />
            </label>
            <label className="field">Password
              <input className="input" type="password" autoComplete="current-password" value={password}
                     onChange={(e) => setPassword(e.target.value)} />
            </label>
          </>
        ) : (
          <>
            <label className="field">Access token
              <input className="input" type="password" autoComplete="current-password" autoFocus value={token}
                     onChange={(e) => setToken(e.target.value)} />
            </label>
            <p className="small muted" style={{ margin: 0 }}>The <code>ARGUS_TOKEN</code> from the server's <code>.env</code>.</p>
          </>
        )}
        <p className="small muted" style={{ margin: 0 }}>You stay signed in on this browser for 90 days.</p>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={busy || !ready}>{busy ? "Signing in…" : "Sign in"}</button>
        {methods.includes(other) && (
          <button type="button" className="btn" onClick={() => { setMethod(other); setError(null); }}>
            {other === "token" ? "Use the server token instead" : "Use a username and password"}
          </button>
        )}
      </form>
    </main>
  );
}

function Main({ auth }: { auth: AuthStatus }) {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  const [portfolios, setPortfolios] = useState<PortfolioRef[] | null>(null);
  const [current, setCurrent] = useState<string>(() => {
    try {
      return localStorage.getItem(KEY) ?? "";
    } catch {
      return "";
    }
  });

  // Also rerun after a portfolio is deleted, so the picker drops it and the selection moves on.
  const loadPortfolios = useCallback(() => {
    api.portfolios().then((ps) => {
      setPortfolios(ps);
      setCurrent((c) => (ps.some((p) => p.name === c) || (c === ALL && ps.length > 1) ? c : ps[0]?.name ?? ""));
    }, () => setPortfolios([]));
  }, []);
  useEffect(loadPortfolios, [loadPortfolios]);

  useEffect(() => {
    try {
      if (current) localStorage.setItem(KEY, current);
    } catch {
      /* ignore */
    }
  }, [current]);

  const { data: live, connected } = useLive(current || undefined);
  const signOut = () => { api.logout().finally(() => window.location.reload()); };
  const signedInAs = auth.account ? `Signed in as ${auth.account.username}` : "Signed in with the server token";
  const signOutLabel = `Sign out${auth.account ? ` ${auth.account.username}` : ""}`;

  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="topbar" onKeyDown={(e) => {
        if (e.key === "Escape" && menuOpen) {
          setMenuOpen(false);
          menuButton.current?.focus();
        }
      }}>
        <div className="brand"><span className="brand-dot" aria-hidden />Argus</div>
        <button ref={menuButton} className="btn menu-toggle" aria-expanded={menuOpen} aria-controls="primary-nav"
                onClick={() => setMenuOpen((open) => !open)}>{menuOpen ? "Close" : "Menu"}</button>
        <nav id="primary-nav" className="nav" aria-label="Main navigation" data-open={menuOpen}
             onClick={(e) => { if ((e.target as HTMLElement).closest("a")) setMenuOpen(false); }}>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/watchlist">Watchlist</NavLink>
          <NavLink to="/transactions">Transactions</NavLink>
          <NavLink to="/analysis">Analysis</NavLink>
          <NavLink to="/markets">Markets</NavLink>
          <NavLink to="/screener">Screener</NavLink>
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/dcf">DCF</NavLink>
          <NavLink to="/alerts">Alerts{live?.alerts_fired?.length ? ` · ${live.alerts_fired.length}` : ""}</NavLink>
          <NavLink to="/data">Data</NavLink>
          {auth.required && <button className="nav-sign-out" title={signedInAs} onClick={signOut}>{signOutLabel}</button>}
        </nav>
        {portfolios && portfolios.length > 0 && (
          <select className="portfolio-picker" value={current} onChange={(e) => setCurrent(e.target.value)} aria-label="Portfolio">
            {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
            {portfolios.length > 1 && <option value={ALL}>All portfolios</option>}
          </select>
        )}
        <TickerSearch />
        <div className="spacer" />
        <LiveBadge live={live} connected={connected} />
        <ThemeToggle />
        {auth.required && (
          <button className="btn sign-out" title={signedInAs} onClick={signOut}>{signOutLabel}</button>
        )}
      </header>
      <main id="main-content" tabIndex={-1}>
        <Suspense fallback={<p className="muted">Loading…</p>}>
        {portfolios === null ? <p className="muted">Loading…</p>
          : portfolios.length === 0 ? (
            <Routes>
              <Route path="/data" element={<Data onPortfoliosChanged={loadPortfolios} />} />
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
              <Route path="/dcf" element={<Dcf />} />
              <Route path="/dcf/:symbol" element={<Dcf />} />
              <Route path="/analysis" element={<Analysis portfolio={current} />} />
              <Route path="/markets" element={<Markets />} />
              <Route path="/screener" element={<Screener />} />
              <Route path="/alerts" element={<Alerts live={live} />} />
              <Route path="/data" element={<Data onPortfoliosChanged={loadPortfolios} />} />
            </Routes>
          )}
        </Suspense>
      </main>
    </>
  );
}
