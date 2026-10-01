import { useEffect, useId, useRef, useState } from "react";
import { api, type SearchHit } from "../api";

const MAX = 5;
const DEBOUNCE_MS = 150;

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  "aria-label"?: string;
}

/** Text input for one or more tickers ("TSLA, COST") that suggests completions for the last one. */
export function TickerInput({ value, onChange, placeholder, "aria-label": label }: Props) {
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const seq = useRef(0);
  const listId = useId();

  // Only the token being typed (after the last comma or space) is completed.
  const head = value.match(/^(.*[\s,])?/)?.[0] ?? "";
  const token = value.slice(head.length).trim();

  useEffect(() => {
    const n = ++seq.current;
    if (!token) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      api.search(token, MAX).then((r) => {
        if (n !== seq.current) return; // a newer keystroke won
        setHits(r);
        setActive(0);
      }, () => n === seq.current && setHits([]));
    }, DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [token]);

  const shown = open && token ? hits : [];

  const pick = (h: SearchHit) => {
    onChange(head + h.symbol);
    setOpen(false);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!shown.length) return;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const step = e.key === "ArrowDown" ? 1 : -1;
      setActive((a) => (a + step + shown.length) % shown.length);
    } else if (e.key === "Enter" && shown[active] && shown[active].symbol !== token.toUpperCase()) {
      e.preventDefault(); // complete first; a second Enter submits the form
      pick(shown[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="combo">
      <input className="input" value={value} placeholder={placeholder} aria-label={label} autoComplete="off"
             role="combobox" aria-expanded={shown.length > 0} aria-controls={listId} aria-autocomplete="list"
             aria-activedescendant={shown.length ? `${listId}-${active}` : undefined}
             onChange={(e) => { onChange(e.target.value); setOpen(true); }}
             onKeyDown={onKeyDown} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} />
      {shown.length > 0 && (
        <ul className="combo-list" role="listbox" id={listId}>
          {shown.map((h, i) => (
            <li key={h.symbol} id={`${listId}-${i}`} role="option" aria-selected={i === active}
                className={i === active ? "active" : undefined}
                onMouseDown={(e) => { e.preventDefault(); pick(h); }} onMouseEnter={() => setActive(i)}>
              <strong>{h.symbol}</strong>
              <span className="combo-name">{h.name}</span>
              {h.type && h.type !== "Common Stock" && <span className="tag">{h.type === "ETP" ? "ETF" : h.type}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
