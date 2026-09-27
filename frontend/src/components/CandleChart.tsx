import {
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import type { HistoryResponse, Quote } from "../api";
import { price } from "../format";

export type Overlay = "sma20" | "sma50" | "sma200" | "bb20";
export type Pane = "volume" | "rsi14" | "macd";

// Overlays are categorical identities: fixed slot order, never recolored by rank.
export const OVERLAY_COLOR: Record<Overlay, string> = {
  sma20: "var(--series-1)",
  sma50: "var(--series-2)",
  sma200: "var(--series-3)",
  bb20: "var(--muted)",
};

const css = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const resolve = (color: string) => (color.startsWith("var(") ? css(color.slice(4, -1)) : color);

/** Daily bars keyed by New York calendar date; intraday bars shifted so the axis reads in ET. */
function toTime(iso: string, intraday: boolean): Time {
  const d = new Date(iso);
  if (!intraday) {
    return d.toLocaleDateString("en-CA", { timeZone: "America/New_York" }) as Time; // YYYY-MM-DD
  }
  const ny = new Date(d.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const utc = new Date(d.toLocaleString("en-US", { timeZone: "UTC" }));
  return ((d.getTime() + (ny.getTime() - utc.getTime())) / 1000) as UTCTimestamp;
}

interface Props {
  data: HistoryResponse;
  overlays: Overlay[];
  panes: Pane[];
  live?: Quote | null;
}

export function CandleChart({ data, overlays, panes, live }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [legend, setLegend] = useState<string>("");
  const [themeTick, setThemeTick] = useState(0);

  // Rebuild on theme change so the chart picks up the new tokens.
  useEffect(() => {
    const bump = () => setThemeTick((t) => t + 1);
    const mq = matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", bump);
    window.addEventListener("argus-theme", bump);
    return () => {
      mq.removeEventListener("change", bump);
      window.removeEventListener("argus-theme", bump);
    };
  }, []);

  useEffect(() => {
    if (!el.current) return;
    const intraday = data.interval !== "1d";
    const chart = createChart(el.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: css("--surface") },
        textColor: css("--muted"),
        fontFamily: css("--font"),
        attributionLogo: false,
        panes: { separatorColor: css("--grid") },
      },
      grid: { vertLines: { visible: false }, horzLines: { color: css("--grid") } },
      rightPriceScale: { borderColor: css("--axis") },
      timeScale: { borderColor: css("--axis"), timeVisible: intraday, secondsVisible: false },
      crosshair: { horzLine: { labelBackgroundColor: css("--text-2") }, vertLine: { labelBackgroundColor: css("--text-2") } },
    });
    chartRef.current = chart;

    const times = data.bars.map((b) => toTime(b.ts, intraday));
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: css("--candle-up"), downColor: css("--candle-down"), borderVisible: false,
      wickUpColor: css("--candle-up"), wickDownColor: css("--candle-down"),
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    candles.setData(data.bars.map((b, i) => ({ time: times[i], open: b.o, high: b.h, low: b.l, close: b.c })));

    const line = (values: (number | null)[] | undefined, color: string, pane = 0, width: 1 | 2 = 2) => {
      if (!values) return;
      const s = chart.addSeries(LineSeries, {
        color: resolve(color), lineWidth: width, priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerVisible: false,
      }, pane);
      s.setData(values.flatMap((v, i) => (v == null ? [] : [{ time: times[i], value: v }])));
      return s;
    };

    const ind = data.indicators ?? {};
    for (const o of overlays) {
      const v = ind[o];
      if (o === "bb20" && v && !Array.isArray(v)) {
        line(v.upper, OVERLAY_COLOR.bb20, 0, 1);
        line(v.lower, OVERLAY_COLOR.bb20, 0, 1);
      } else if (Array.isArray(v)) {
        line(v, OVERLAY_COLOR[o]);
      }
    }

    let paneIndex = 1;
    if (panes.includes("volume")) {
      const vol = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceLineVisible: false,
        lastValueVisible: false }, paneIndex);
      vol.setData(data.bars.map((b, i) => ({
        time: times[i], value: b.v,
        color: resolve(b.c >= b.o ? "var(--candle-up)" : "var(--candle-down)") + "66",
      })));
      paneIndex++;
    }
    const rsi = ind.rsi14;
    if (panes.includes("rsi14") && Array.isArray(rsi)) {
      const s = line(rsi, "var(--series-1)", paneIndex);
      s?.createPriceLine({ price: 70, color: css("--axis"), lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "" });
      s?.createPriceLine({ price: 30, color: css("--axis"), lineWidth: 1, lineStyle: 0, axisLabelVisible: true, title: "" });
      paneIndex++;
    }
    const macd = ind.macd;
    if (panes.includes("macd") && macd && !Array.isArray(macd)) {
      const h = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, paneIndex);
      h.setData(macd.hist.flatMap((v, i) => (v == null ? [] : [{
        time: times[i], value: v, color: resolve(v >= 0 ? "var(--candle-up)" : "var(--candle-down)") + "88" }])));
      line(macd.macd, "var(--series-1)", paneIndex);
      line(macd.signal, "var(--series-2)", paneIndex);
      paneIndex++;
    }
    const allPanes = chart.panes();
    allPanes.forEach((p, i) => p.setStretchFactor(i === 0 ? 4 : 1));

    const last = data.bars[data.bars.length - 1];
    const describe = (b: typeof last | undefined) =>
      b ? `O ${price(b.o)}  H ${price(b.h)}  L ${price(b.l)}  C ${price(b.c)}  Vol ${b.v.toLocaleString("en-US")}` : "";
    setLegend(describe(last));
    const onMove = (p: MouseEventParams) => {
      const i = p.time == null ? -1 : times.indexOf(p.time);
      setLegend(describe(i >= 0 ? data.bars[i] : last));
    };
    chart.subscribeCrosshairMove(onMove);
    chart.timeScale().fitContent();

    return () => {
      chart.unsubscribeCrosshairMove(onMove);
      chart.remove();
      chartRef.current = null;
    };
  }, [data, overlays, panes, themeTick]);

  // Live price on daily charts: extend today's candle, or start it if the last bar is an earlier session.
  useEffect(() => {
    const chart = chartRef.current;
    const last = data.bars[data.bars.length - 1];
    if (!chart || !last || !live || data.interval !== "1d") return;
    const series = chart.panes()[0]?.getSeries()[0];
    if (!series) return;
    const lastDay = toTime(last.ts, false) as string;
    const quoteDay = live.session_date;
    if (quoteDay < lastDay) return;
    const bar = quoteDay === lastDay
      ? { time: lastDay, open: last.o, high: Math.max(last.h, live.price), low: Math.min(last.l, live.price), close: live.price }
      : { time: quoteDay, open: live.open ?? live.price, high: Math.max(live.high ?? live.price, live.price),
          low: Math.min(live.low ?? live.price, live.price), close: live.price };
    series.update(bar as never);
  }, [live, data]);

  return (
    <div className="chart-box">
      <div className="chart-legend num">{legend}</div>
      <div ref={el} style={{ position: "absolute", inset: 0 }} />
    </div>
  );
}
