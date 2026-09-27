import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api, type PortfolioRef } from "./api";
import { LiveBadge } from "./components/LiveBadge";
import { ThemeToggle } from "./components/ThemeToggle";
import { Alerts } from "./pages/Alerts";
import { Analysis } from "./pages/Analysis";
import { Compare } from "./pages/Compare";
import { Dashboard } from "./pages/Dashboard";
import { Ticker } from "./pages/Ticker";
import { Transactions } from "./pages/Transactions";
import { Watchlist } from "./pages/Watchlist";
import { useLive } from "./useLive";

const KEY = "argus.portfolio";

export function App() {
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
      setCurrent((c) => (ps.some((p) => p.name === c) ? c : ps[0]?.name ?? ""));
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
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/alerts">Alerts{live?.alerts_fired?.length ? ` · ${live.alerts_fired.length}` : ""}</NavLink>
        </nav>
        {portfolios && portfolios.length > 0 && (
          <select value={current} onChange={(e) => setCurrent(e.target.value)} aria-label="Portfolio">
            {portfolios.map((p) => <option key={p.id} value={p.name}>{p.name}</option>)}
          </select>
        )}
        <div className="spacer" />
        <LiveBadge live={live} connected={connected} />
        <ThemeToggle />
      </header>
      <main>
        {portfolios === null ? <p className="muted">Loading…</p>
          : portfolios.length === 0 ? (
            <div className="card">
              <h2>No portfolios yet</h2>
              <p>Import one from Investing.com:</p>
              <pre>uv run argus import investing data/&lt;name&gt;_Holdings_MMDDYYYY.csv --opening-through YYYY-MM-DD</pre>
            </div>
          ) : (
            <Routes>
              <Route path="/" element={<Dashboard portfolio={current} live={live} />} />
              <Route path="/t/:symbol" element={<Ticker portfolio={current} live={live} />} />
              <Route path="/watchlist" element={<Watchlist live={live} />} />
              <Route path="/transactions" element={<Transactions portfolio={current} />} />
              <Route path="/compare" element={<Compare portfolio={current} />} />
              <Route path="/analysis" element={<Analysis portfolio={current} />} />
              <Route path="/alerts" element={<Alerts live={live} />} />
            </Routes>
          )}
      </main>
    </>
  );
}
