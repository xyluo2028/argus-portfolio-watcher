import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TickerInput } from "./TickerInput";

/** Top-bar search: pick a suggestion (or type a symbol and press Enter) to open its page. "/" focuses it. */
export function TickerSearch() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const form = useRef<HTMLFormElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey || el.closest("input, textarea, select, [contenteditable]")) return;
      e.preventDefault();
      form.current?.querySelector("input")?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  const go = (s: string) => {
    const symbol = s.trim().split(/[\s,]+/)[0]?.toUpperCase();
    if (!symbol) return;
    navigate(`/t/${encodeURIComponent(symbol)}`);
    setQ("");
    form.current?.querySelector("input")?.blur(); // closes the phone keyboard
  };

  return (
    <form ref={form} role="search" className="ticker-search" onSubmit={(e) => { e.preventDefault(); go(q); }}>
      <TickerInput value={q} onChange={setQ} onPick={go} aria-label="Search ticker or company"
                   placeholder={matchMedia("(pointer: coarse)").matches ? "Search ticker or company" : "Search ticker or company   /"} />
    </form>
  );
}
