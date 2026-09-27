import type { StreamUpdate } from "../api";
import { nyTime } from "../format";

const LABEL = { pre: "Pre-market", regular: "Market open", post: "After hours", closed: "Market closed" } as const;

export function LiveBadge({ live, connected }: { live: StreamUpdate | null; connected: boolean }) {
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
    <span className={`badge ${streaming ? "live" : ""}`} title={connected ? "Connected to Argus" : "Reconnecting to Argus…"}>
      <span className="dot" aria-hidden />
      <strong>{LABEL[market.session]}</strong>
      <span className="muted">{connected ? detail : "reconnecting…"}</span>
    </span>
  );
}
