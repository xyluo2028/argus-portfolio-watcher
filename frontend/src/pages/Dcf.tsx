import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api, type DcfData, type DcfInputs, type DcfMetricKey, type DcfSaved } from "../api";
import { TickerInput } from "../components/TickerInput";
import { METRIC_ORDER, MULTIPLE_LABEL, defaultMetric, defaults, historicalGrowth, project, type DcfResult } from "../dcf";
import { big, pct, price } from "../format";

const LAST = "argus.dcf.symbol";
type Field = Exclude<keyof DcfInputs, "metric">;
type Form = { metric: DcfMetricKey } & Record<Field, string>;

// The base is typed in millions, like a filing's tables; the rest as they are.
const toForm = (i: DcfInputs): Form => ({
  metric: i.metric, base: String(Math.round(i.base / 1e6)), years: String(i.years), growth: String(i.growth),
  decay: String(i.decay), multiple: String(i.multiple), target_return: String(i.target_return), dps: String(i.dps),
  dividend_growth: String(i.dividend_growth), share_change: String(i.share_change),
});
const fromForm = (f: Form): DcfInputs => {
  const n = (k: Field) => (f[k].trim() === "" ? NaN : Number(f[k]));
  return { metric: f.metric, base: n("base") * 1e6, years: Math.round(n("years")), growth: n("growth"), decay: n("decay"),
           multiple: n("multiple"), target_return: n("target_return"), dps: n("dps"), dividend_growth: n("dividend_growth"),
           share_change: n("share_change") };
};
const same = (a: DcfInputs, b: DcfInputs) => (Object.keys(a) as (keyof DcfInputs)[]).every((k) => a[k] === b[k]);
const fmtDate = (iso: string) => new Date(iso.length === 10 ? `${iso}T12:00:00Z` : iso)
  .toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", ...(iso.length === 10 ? { timeZone: "UTC" } : {}) });
const num = (v: number | null | undefined, d = 1) => (v == null ? "–" : v.toFixed(d));

export function Dcf() {
  const { symbol: param } = useParams();
  const navigate = useNavigate();
  const symbol = param?.toUpperCase() ?? "";
  const [q, setQ] = useState("");
  const [models, setModels] = useState<{ symbol: string; updated_at: string }[]>([]);
  const [data, setData] = useState<DcfData | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [saved, setSaved] = useState<DcfSaved | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.valuationModels().then(setModels, () => setModels([])); }, [saved]);

  // No symbol in the address: reopen the last one.
  useEffect(() => {
    if (symbol) return;
    try {
      const last = localStorage.getItem(LAST);
      if (last) navigate(`/dcf/${encodeURIComponent(last)}`, { replace: true });
    } catch { /* ignore */ }
  }, [symbol, navigate]);

  useEffect(() => {
    if (!symbol) return;
    let stale = false;
    setData(null); setError(null); setForm(null); setSaved(null);
    api.valuation(symbol).then((d) => {
      if (stale) return;
      setData(d);
      setSaved(d.saved);
      setForm(toForm(d.saved?.inputs ?? defaults(d, defaultMetric(d))));
      try { localStorage.setItem(LAST, symbol); } catch { /* ignore */ }
    }, (e) => { if (!stale) setError(e); });
    return () => { stale = true; };
  }, [symbol]);

  const inputs = form ? fromForm(form) : null;
  const result = useMemo(() => (inputs && data?.price && data.shares ? project(inputs, data.price, data.shares) : null),
                         [JSON.stringify(inputs), data]); // eslint-disable-line react-hooks/exhaustive-deps
  const dirty = !!inputs && (!saved || !same(inputs, saved.inputs));

  const set = (k: Field, v: string | number) => setForm((f) => f && { ...f, [k]: String(v) });
  const pickMetric = (k: DcfMetricKey) => {
    if (!data || !form) return;
    const d = toForm(defaults(data, k)); // only what depends on the metric changes
    setForm({ ...form, metric: k, base: d.base, growth: d.growth, multiple: d.multiple });
  };
  const save = async () => {
    if (!inputs || !result) return;
    setBusy(true);
    try { setSaved((await api.saveValuation(symbol, inputs)).saved); } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  };
  const forget = async () => {
    setBusy(true);
    try { await api.saveValuation(symbol, null); setSaved(null); } finally { setBusy(false); }
  };

  const go = (s: string) => {
    const sym = s.trim().split(/[\s,]+/)[0]?.toUpperCase();
    if (sym) { setQ(""); navigate(`/dcf/${encodeURIComponent(sym)}`); }
  };

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
          <div>
            <h2 style={{ margin: 0 }}>DCF calculator{data?.company ? <span className="muted small"> · <Link to={`/t/${symbol}`}>{symbol}</Link> · {data.company}</span> : null}</h2>
            <p className="small muted" style={{ margin: "4px 0 0" }}>
              Grow a cash flow or earnings figure, value it at an exit multiple, and discount back at the return you want.
            </p>
          </div>
          <form className="row" style={{ gap: 8, flex: "0 1 340px" }} onSubmit={(e) => { e.preventDefault(); go(q); }}>
            <TickerInput value={q} onChange={setQ} onPick={go} placeholder="Ticker" aria-label="Ticker to value" />
            <button className="btn">Open</button>
          </form>
        </div>
        {models.length > 0 && (
          <div className="suggest" style={{ marginTop: 10 }}>
            <span className="lbl">Saved</span>
            {models.map((m) => (
              <button key={m.symbol} aria-pressed={m.symbol === symbol} onClick={() => navigate(`/dcf/${m.symbol}`)}
                      title={`Saved ${fmtDate(m.updated_at)}`}>{m.symbol}</button>
            ))}
          </div>
        )}
      </section>

      {!symbol ? <p className="muted">Pick a ticker to value.</p>
        : error ? <div className="card"><p className="error" style={{ margin: 0 }}>{error.message}</p>{error.hint && <p className="small muted">{error.hint}</p>}</div>
        : !data || !form || !inputs ? <p className="muted">Loading {symbol}'s filings and estimates…</p>
        : (
          <div className="dcf-grid">
            <Inputs data={data} form={form} inputs={inputs} set={set} setForm={setForm} pickMetric={pickMetric} />
            <div className="stack" style={{ minWidth: 0 }}>
              <section className="card">
                <div className="row" style={{ justifyContent: "space-between" }}>
                  <div className="row" style={{ gap: 8 }}>
                    {saved && <span className="small muted">Saved {fmtDate(saved.updated_at)}{dirty ? " · changed since" : ""}</span>}
                    {!saved && <span className="small muted">Not saved</span>}
                  </div>
                  <div className="row" style={{ gap: 8 }}>
                    <button className="btn ghost small" onClick={() => setForm(toForm(defaults(data, form.metric)))}>Reset inputs</button>
                    {saved && <button className="btn ghost small" disabled={busy} onClick={forget}>Delete saved</button>}
                    <button className="btn primary small" disabled={busy || !result || !dirty} onClick={save}>{busy ? "Saving…" : "Save"}</button>
                  </div>
                </div>
              </section>
              {result ? <Results data={data} inputs={inputs} r={result} />
                : <section className="card"><p className="muted" style={{ margin: 0 }}>
                    {(data.metrics[form.metric].base ?? 0) <= 0 && inputs.base <= 0
                      ? `${data.metrics[form.metric].label} isn't positive, so there's nothing to grow: pick another metric or type a value.`
                      : "Fill in every input to see a value."}
                  </p></section>}
              {result && <Charts data={data} inputs={inputs} r={result} />}
              {result && <Calculation data={data} inputs={inputs} r={result} />}
            </div>
          </div>
        )}
    </div>
  );
}

function Hint({ items }: { items: [string, number | null | undefined, (v: number) => void, string?][] }) {
  const shown = items.filter(([, v]) => v != null && Number.isFinite(v));
  if (!shown.length) return null;
  return (
    <div className="suggest dcf-hint">
      {shown.map(([label, v, apply, text]) => (
        <button key={label} type="button" onClick={() => apply(v!)} title="Use this value">{label} {text ?? num(v)}</button>
      ))}
    </div>
  );
}

function Inputs({ data, form, inputs, set, setForm, pickMetric }: {
  data: DcfData; form: Form; inputs: DcfInputs; set: (k: Field, v: string | number) => void;
  setForm: React.Dispatch<React.SetStateAction<Form | null>>; pickMetric: (k: DcfMetricKey) => void;
}) {
  const m = data.metrics[form.metric];
  const mult = MULTIPLE_LABEL[form.metric];
  const round1 = (v: number) => Math.round(v * 10) / 10;
  const hist = historicalGrowth(data, form.metric);
  const fill = (g: number | null | undefined, extra: Partial<Form> = {}) =>
    setForm((f) => f && { ...f, ...(g != null ? { growth: String(round1(g)) } : {}), ...extra });
  const nonUsd = m.currency && m.currency !== "USD";

  return (
    <section className="card dcf-inputs">
      <label className="field"><span>Metric</span>
        <div className="row" style={{ gap: 8, flexWrap: "nowrap" }}>
          <select value={form.metric} onChange={(e) => pickMetric(e.target.value as DcfMetricKey)} style={{ flex: 1, minWidth: 0 }}>
            {METRIC_ORDER.map((k) => (
              <option key={k} value={k}>{data.metrics[k].label}{data.metrics[k].base == null ? " (none recent)" : ""}</option>
            ))}
          </select>
          <span className="dcf-unit">
            <input className="input num" inputMode="decimal" value={form.base} onChange={(e) => set("base", e.target.value)}
                   aria-label="Starting value, millions" style={{ width: 120 }} /><span className="muted small">$M</span>
          </span>
        </div>
      </label>
      <p className="small muted dcf-note">
        {m.base != null
          ? <>{m.base_basis === "last four quarters" ? "Trailing 12 months" : "Fiscal year"} to {fmtDate(m.base_end!)}: {big(m.base)} · SEC filings
            {Math.round(m.base / 1e6) !== Math.round(inputs.base / 1e6) && <> · <button type="button" className="linkish" onClick={() => set("base", Math.round(m.base! / 1e6))}>use it</button></>}</>
          : "No recent figure in SEC filings: type one in."}
        {nonUsd && <span className="warn"> Reported in {m.currency}, while the price is in USD: convert before trusting the result.</span>}
      </p>

      <div className="dcf-fill">
        <span className="small muted">Fill from</span>
        <button type="button" className="btn small" disabled={hist == null && m.multiple.median_5y == null}
                onClick={() => fill(hist, {
                  ...(m.multiple.median_5y != null ? { multiple: String(round1(m.multiple.median_5y)) } : {}),
                  ...(data.share_change != null ? { share_change: String(round1(data.share_change)) } : {}),
                  ...(data.dividend_growth_5y != null ? { dividend_growth: String(round1(data.dividend_growth_5y)) } : {}),
                })}
                title="Growth: the metric's 5-year rate (else 3-year). Exit multiple: its 5-year median. Share count and dividend: their recent rates.">
          Historical averages
        </button>
        <button type="button" className="btn small" disabled={m.growth.analyst == null} onClick={() => fill(m.growth.analyst)}
                title={m.growth.analyst_basis ? `Growth: ${m.growth.analyst_basis} (Yahoo)` : "No analyst estimate"}>
          Analyst estimates
        </button>
      </div>

      <label className="field"><span>Years to project</span>
        <input className="input num" inputMode="numeric" value={form.years} onChange={(e) => set("years", e.target.value)} />
      </label>
      {inputs.years < 5 && <p className="small warn dcf-note">With under 5 years, the exit multiple carries most of the value.</p>}

      <label className="field"><span>How fast will {m.label.toLowerCase()} grow? <span className="muted">% a year</span></span>
        <input className="input num" inputMode="decimal" value={form.growth} onChange={(e) => set("growth", e.target.value)} />
      </label>
      <Hint items={[["5y", m.growth.hist_5y, (v) => set("growth", round1(v)), pct(m.growth.hist_5y, 1)],
                    ["3y", m.growth.hist_3y, (v) => set("growth", round1(v)), pct(m.growth.hist_3y, 1)],
                    ["analysts", m.growth.analyst, (v) => set("growth", round1(v)), pct(m.growth.analyst, 1)]]} />

      <label className="field"><span>Growth decay <span className="muted">% a year</span></span>
        <input className="input num" inputMode="decimal" value={form.decay} onChange={(e) => set("decay", e.target.value)} />
      </label>
      <p className="small muted dcf-note">Each year's growth is this much lower than the year before's: 20% growth with 20% decay runs 20, 16, 12.8…</p>

      <label className="field"><span>Exit multiple <span className="muted">{mult}</span></span>
        <input className="input num" inputMode="decimal" value={form.multiple} onChange={(e) => set("multiple", e.target.value)} />
      </label>
      <Hint items={[["today", m.multiple.current, (v) => set("multiple", round1(v))],
                    ["5y median", m.multiple.median_5y, (v) => set("multiple", round1(v))],
                    ["5y low quartile", m.multiple.p25_5y, (v) => set("multiple", round1(v))],
                    ["high quartile", m.multiple.p75_5y, (v) => set("multiple", round1(v))]]} />

      <label className="field"><span>Target return <span className="muted">% a year</span></span>
        <input className="input num" inputMode="decimal" value={form.target_return} onChange={(e) => set("target_return", e.target.value)} />
      </label>

      <div className="grid-2" style={{ gap: 10 }}>
        <label className="field"><span>Dividend per share <span className="muted">$ a year</span></span>
          <input className="input num" inputMode="decimal" value={form.dps} onChange={(e) => set("dps", e.target.value)} />
        </label>
        <label className="field"><span>Dividend growth <span className="muted">%</span></span>
          <input className="input num" inputMode="decimal" value={form.dividend_growth} onChange={(e) => set("dividend_growth", e.target.value)} />
        </label>
      </div>
      <Hint items={[["today", data.dps || null, (v) => set("dps", Math.round(v * 100) / 100), `$${num(data.dps, 2)}`],
                    ["5y growth", data.dividend_growth_5y, (v) => set("dividend_growth", round1(v)), pct(data.dividend_growth_5y, 1)]]} />

      <label className="field"><span>Share count change <span className="muted">% a year, negative = buybacks</span></span>
        <input className="input num" inputMode="decimal" value={form.share_change} onChange={(e) => set("share_change", e.target.value)} />
      </label>
      <Hint items={[[`last ${data.share_change_years ?? ""}y`, data.share_change, (v) => set("share_change", round1(v)), pct(data.share_change, 1)]]} />
    </section>
  );
}

function Results({ data, inputs, r }: { data: DcfData; inputs: DcfInputs; r: DcfResult }) {
  const p = data.price!;
  const verdict = r.upsidePct > 5 ? ["Undervalued", "up"] : r.upsidePct < -5 ? ["Overvalued", "down"] : ["Fairly valued", ""];
  const max = Math.max(p, r.fairValue, data.analyst_target ?? 0) * 1.12;
  const at = (v: number) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`;
  return (
    <div className="grid-2">
      <section className="card">
        <div className="row" style={{ gap: 10, marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Result</h2>
          <span className={`verdict ${verdict[1] === "up" ? "beat" : verdict[1] === "down" ? "miss" : "in_line"}`}>{verdict[0]}</span>
        </div>
        <p style={{ margin: "0 0 4px" }}>
          Fair value is <strong className={verdict[1]}>{pct(Math.abs(r.upsidePct), 1).replace(/^[+−]/, "")} {r.upsidePct >= 0 ? "above" : "below"}</strong> today's price.
        </p>
        <p style={{ margin: "0 0 4px" }}>Return a year from today's price: <strong>{pct(r.cagrPct, 1)}</strong>.</p>
        <p style={{ margin: 0 }}>To earn your {inputs.target_return}% target, buy at or below <strong>${price(r.fairValue)}</strong>.</p>
        <div className="dcf-track" role="img" aria-label={`Today ${price(p)}, fair value ${price(r.fairValue)}`}>
          <div className="dcf-track-fill" style={{ width: at(p) }} />
          <span className="dcf-mark today" style={{ left: at(p) }}><span>Today ${price(p)}</span></span>
          <span className="dcf-mark fair" style={{ left: at(r.fairValue) }}><span>Fair value ${price(r.fairValue)}</span></span>
        </div>
      </section>
      <section className="card">
        <table className="dcf-stats">
          <tbody>
            <tr><th>Today's price</th><td /><td>${price(p)}</td></tr>
            <tr><th>Price in {inputs.years} {inputs.years === 1 ? "year" : "years"}</th>
              <td><span className={`verdict ${r.futureChangePct >= 0 ? "beat" : "miss"}`}>{pct(r.futureChangePct, 1)}</span></td><td>${price(r.futurePrice)}</td></tr>
            <tr><th>Dividends on the way</th><td /><td>{r.dividends > 0 ? `$${price(r.dividends)}` : "–"}</td></tr>
            <tr><th>Fair value</th>
              <td><span className={`verdict ${r.upsidePct >= 0 ? "beat" : "miss"}`}>{pct(r.upsidePct, 1)}</span></td><td><strong>${price(r.fairValue)}</strong></td></tr>
            <tr><th>Return a year</th><td /><td className={r.cagrPct != null && r.cagrPct >= inputs.target_return ? "up" : "down"}>{pct(r.cagrPct, 1)}</td></tr>
            {data.analyst_target != null && (
              <tr className="muted"><th>Analysts' target</th><td className="small">{data.analyst_count ? `${data.analyst_count} analysts` : ""}</td><td>${price(data.analyst_target)}</td></tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

type Bar = { label: string; value: number; projected: boolean; note?: string };

function Bars({ bars, fmt, aria }: { bars: Bar[]; fmt: (v: number) => string; aria: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const W = 640, H = 220, pad = { l: 52, r: 8, t: 12, b: 22 };
  const lo = Math.min(0, ...bars.map((b) => b.value)), hi = Math.max(0, ...bars.map((b) => b.value)) || 1;
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - (v - lo) / (hi - lo));
  const band = (W - pad.l - pad.r) / bars.length, bw = Math.min(34, band * 0.68);
  const shown = bars[hover ?? bars.length - 1];
  const step = Math.ceil(bars.length / 12); // label every year until they'd crowd
  return (
    <div>
      <div className="small dcf-readout"><strong>{shown.label}</strong> {fmt(shown.value)} <span className="muted">{shown.projected ? "projected" : shown.note ?? "reported"}</span></div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={aria} onPointerLeave={() => setHover(null)}>
        {[lo, (lo + hi) / 2, hi].filter((v, i, a) => a.indexOf(v) === i).map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="var(--grid)" />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="var(--muted)">{fmt(v)}</text>
          </g>
        ))}
        {lo < 0 && <line x1={pad.l} x2={W - pad.r} y1={y(0)} y2={y(0)} stroke="var(--axis)" />}
        {bars.map((b, i) => {
          const x = pad.l + band * i + (band - bw) / 2, top = y(Math.max(0, b.value)), bottom = y(Math.min(0, b.value));
          return (
            <g key={`${b.label}${i}`} onPointerEnter={() => setHover(i)} onPointerDown={() => setHover(i)}>
              <rect x={pad.l + band * i} y={pad.t} width={band} height={H - pad.t - pad.b} fill="transparent" />
              <rect x={x} y={top} width={bw} height={Math.max(1, bottom - top)} rx={3}
                    fill={b.value < 0 ? "var(--down)" : "var(--series-1)"} opacity={b.projected ? 0.42 : 1}
                    stroke={hover === i ? "var(--text)" : "none"} />
              {i % step === 0 && <text x={x + bw / 2} y={H - 6} textAnchor="middle" fontSize={10} fill="var(--muted)">{b.label}</text>}
            </g>
          );
        })}
      </svg>
      <div className="row small muted" style={{ gap: 14 }}>
        <span className="row" style={{ gap: 6 }}><span className="dcf-swatch" />Reported</span>
        <span className="row" style={{ gap: 6 }}><span className="dcf-swatch" style={{ opacity: 0.42 }} />Projected</span>
      </div>
    </div>
  );
}

function MultipleLine({ data, inputs }: { data: DcfData; inputs: DcfInputs }) {
  const m = data.metrics[inputs.metric].multiple;
  const label = MULTIPLE_LABEL[inputs.metric];
  const [hover, setHover] = useState<number | null>(null);
  const pts = m.history;
  if (pts.length < 2) return <p className="muted small">Not enough {label} history to chart.</p>;
  const W = 640, H = 220, pad = { l: 40, r: 96, t: 12, b: 22 };
  const vals = [...pts.map((p) => p.v), inputs.multiple, ...(m.median_5y != null ? [m.median_5y] : [])];
  const lo = Math.min(...vals) * 0.9, hi = Math.max(...vals) * 1.05;
  const x = (i: number) => pad.l + (i / (pts.length - 1)) * (W - pad.l - pad.r);
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - (v - lo) / (hi - lo));
  const shown = pts[hover ?? pts.length - 1];
  const years = pts.map((p, i) => [p.date.slice(0, 4), i] as const).filter(([yr], i, a) => i === 0 || a[i - 1][0] !== yr);
  const yLabels = years.filter((_, i) => i % Math.ceil(years.length / 6) === 0);
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const f = ((e.clientX - r.left) / r.width * W - pad.l) / (W - pad.l - pad.r);
    setHover(Math.max(0, Math.min(pts.length - 1, Math.round(f * (pts.length - 1)))));
  };
  // Two reference lines close together: one label above its line, the other below, so they don't overlap.
  const close = m.median_5y != null && Math.abs(y(m.median_5y) - y(inputs.multiple)) < 13;
  const above = close && inputs.multiple >= m.median_5y!;
  const ref = (v: number, text: string, color: string, dash: string, nudge: number) => (
    <g>
      <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke={color} strokeDasharray={dash} strokeWidth={1.5} />
      <text x={W - pad.r + 6} y={y(v) + 4 + nudge} fontSize={11} fill={color === "var(--muted)" ? "var(--muted)" : "var(--text-2)"}>{text}</text>
    </g>
  );
  return (
    <div>
      <div className="small dcf-readout"><strong>{fmtDate(shown.date)}</strong> {label} {shown.v.toFixed(1)}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" onPointerMove={onMove} onPointerDown={onMove} onPointerLeave={() => setHover(null)}
           aria-label={`${label} at each quarter end; 5-year median ${num(m.median_5y)}, your exit multiple ${inputs.multiple}`}>
        {[lo, (lo + hi) / 2, hi].map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="var(--grid)" />
            <text x={pad.l - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="var(--muted)">{v.toFixed(0)}</text>
          </g>
        ))}
        {yLabels.map(([yr, i]) => <text key={yr} x={x(i)} y={H - 6} fontSize={10} fill="var(--muted)" textAnchor="middle">{yr}</text>)}
        <path d={pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.v).toFixed(1)}`).join("")}
              fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" />
        {m.median_5y != null && ref(m.median_5y, `5y median ${m.median_5y.toFixed(1)}`, "var(--muted)", "4 4", close ? (above ? 7 : -7) : 0)}
        {ref(inputs.multiple, `your exit ${inputs.multiple}`, "var(--series-2)", "2 3", close ? (above ? -7 : 7) : 0)}
        {hover != null && <circle cx={x(hover)} cy={y(pts[hover].v)} r={4} fill="var(--series-1)" stroke="var(--surface)" strokeWidth={2} />}
      </svg>
    </div>
  );
}

function Charts({ data, inputs, r }: { data: DcfData; inputs: DcfInputs; r: DcfResult }) {
  const [tab, setTab] = useState<"metric" | "multiple" | "price">("metric");
  const m = data.metrics[inputs.metric];
  const startYear = Number((m.base_end ?? new Date().toISOString()).slice(0, 4));
  const metricBars: Bar[] = [
    ...m.annual.map((a) => ({ label: `FY${a.period_end.slice(2, 4)}`, value: a.value, projected: false, note: `fiscal year to ${fmtDate(a.period_end)}` })),
    ...(m.base_basis === "last four quarters" && m.base != null ? [{ label: "TTM", value: m.base, projected: false, note: `12 months to ${fmtDate(m.base_end!)}` }] : []),
    ...r.rows.map((row) => ({ label: String(startYear + row.year), value: row.metric, projected: true })),
  ];
  const priceBars: Bar[] = [
    { label: "Today", value: data.price!, projected: false, note: "" },
    ...r.rows.map((row) => ({ label: String(startYear + row.year), value: row.price, projected: true })),
  ];
  return (
    <section className="card">
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
        <h2 style={{ margin: 0 }}>Projection</h2>
        <div className="seg" role="tablist">
          {([["metric", m.label], ["multiple", `${MULTIPLE_LABEL[inputs.metric]} history`], ["price", "Price"]] as const).map(([k, l]) => (
            <button key={k} role="tab" aria-selected={tab === k} aria-pressed={tab === k} onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
      </div>
      {tab === "metric" && <Bars bars={metricBars} fmt={(v) => `$${big(v)}`} aria={`${m.label}, reported then projected`} />}
      {tab === "multiple" && <MultipleLine data={data} inputs={inputs} />}
      {tab === "price" && <Bars bars={priceBars} fmt={(v) => `$${price(v)}`} aria="Share price today and at the exit multiple each year" />}
      {tab === "price" && <p className="small muted" style={{ marginBottom: 0 }}>Each year's price is that year's {m.label.toLowerCase()} per share × your exit multiple.</p>}
    </section>
  );
}

function Calculation({ data, inputs, r }: { data: DcfData; inputs: DcfInputs; r: DcfResult }) {
  const label = MULTIPLE_LABEL[inputs.metric];
  const pvExit = r.futurePrice / (1 + inputs.target_return / 100) ** inputs.years;
  return (
    <details className="card">
      <summary><strong>Show calculation</strong></summary>
      <div className="table-wrap" style={{ marginTop: 10 }}>
        <table>
          <thead><tr><th>Year</th><th>Growth</th><th>{data.metrics[inputs.metric].label}</th><th>Shares</th><th>Per share</th><th>Price at {inputs.multiple}× {label.slice(2)}</th><th>Dividend</th></tr></thead>
          <tbody>
            <tr style={{ cursor: "default" }}><td>Now</td><td /><td>${big(inputs.base)}</td><td>{big(data.shares)}</td><td>${(inputs.base / data.shares!).toFixed(2)}</td><td>${price(data.price)}</td><td>{inputs.dps ? `$${inputs.dps.toFixed(2)}` : "–"}</td></tr>
            {r.rows.map((row) => (
              <tr key={row.year} style={{ cursor: "default" }}>
                <td>{row.year}</td><td>{pct(row.growth, 1)}</td><td>${big(row.metric)}</td><td>{big(row.shares)}</td>
                <td>${(row.metric / row.shares).toFixed(2)}</td><td>${price(row.price)}</td><td>{row.dividend ? `$${row.dividend.toFixed(2)}` : "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small" style={{ marginBottom: 0 }}>
        Fair value = ${price(r.futurePrice)} ÷ {(1 + inputs.target_return / 100).toFixed(2)}<sup>{inputs.years}</sup> = ${price(pvExit)}
        {r.dividends > 0 && <>, plus the dividends discounted the same way, ${price(r.fairValue - pvExit)}</>}
        {" "}= <strong>${price(r.fairValue)}</strong>. Return a year = (${price(r.futurePrice)}{r.dividends > 0 ? ` + $${price(r.dividends)} dividends` : ""}) ÷ ${price(data.price)}, over {inputs.years} {inputs.years === 1 ? "year" : "years"}.
        <span className="muted"> Dividends aren't reinvested; today's share count is market cap ÷ price.</span>
      </p>
    </details>
  );
}
