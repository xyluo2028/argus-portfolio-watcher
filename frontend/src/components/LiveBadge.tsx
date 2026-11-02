import { useEffect, useRef } from "react";
import type { StreamUpdate } from "../api";
import { nyTime } from "../format";

const LABEL = { pre: "Pre-market", regular: "Market open", post: "After hours", closed: "Market closed" } as const;

/** Market session and stream status: inline on wide screens; on phones a dropdown that closes on an
 * outside tap (the two are swapped in CSS). */
export function LiveBadge({ live, connected }: { live: StreamUpdate | null; connected: boolean }) {
  const menu = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (e: PointerEvent) => {
      const d = menu.current;
      if (d?.open && !d.contains(e.target as Node)) d.open = false;
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  if (!live) return <span className="badge">Connecting…</span>;
  const { market, stream } = live;
  const streaming = connected && stream.state === "connected";
  const detail =
    market.session === "closed"
      ? `as of ${nyTime(market.last_close)} · opens ${nyTime(market.next_open)}`
      : streaming
        ? `live · streaming ${stream.symbols} symbols`
        : stream.state === "disabled"
          ? "polling each minute (no Finnhub key)"
          : `polling · stream ${stream.state}`;
  return (
    <>
    <span className={`badge market-inline ${streaming ? "live" : ""}`} title={connected ? "Connected to Argus" : "Reconnecting to Argus…"}>
      <span className="dot" aria-hidden />
      <strong>{LABEL[market.session]}</strong>
      <span className="muted">{connected ? detail : "reconnecting…"}</span>
    </span>
    <details ref={menu} className="market-status">
      <summary className={`badge ${streaming ? "live" : ""}`}>
        <span className="dot" aria-hidden />
        <strong>{LABEL[market.session]}</strong>
        <span className="muted">{connected ? "Details ▾" : "Reconnecting…"}</span>
      </summary>
      <div className="market-detail">{connected ? detail : `Reconnecting to Argus… · ${detail}`}</div>
    </details>
    </>
  );
}
