import { useEffect, useState } from "react";
import type { StreamUpdate } from "./api";

/** Subscribe to the server-sent event stream (EventSource reconnects on its own). */
export function useLive(portfolio?: string): { data: StreamUpdate | null; connected: boolean } {
  const [data, setData] = useState<StreamUpdate | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const url = `/api/stream${portfolio ? `?portfolio=${encodeURIComponent(portfolio)}` : ""}`;
    const es = new EventSource(url);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.addEventListener("update", (e) => {
      setConnected(true);
      setData(JSON.parse((e as MessageEvent).data));
    });
    return () => es.close();
  }, [portfolio]);

  return { data, connected };
}
