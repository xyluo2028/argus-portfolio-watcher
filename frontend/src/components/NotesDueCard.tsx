import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ALL, api, type DueNote } from "../api";

function day(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" });
}

/** Notes whose review date is within a week or past, on the portfolio's holdings and on every
 * watchlist symbol (the brief's notes due). Hidden when none are due. */
export function NotesDueCard({ portfolio }: { portfolio: string }) {
  const [notes, setNotes] = useState<DueNote[] | null>(null);

  useEffect(() => {
    let stale = false;
    setNotes(null);
    api.notesDue(portfolio).then((n) => !stale && setNotes(n), () => !stale && setNotes([]));
    return () => { stale = true; };
  }, [portfolio]);

  if (!notes || notes.length === 0) return null;
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  return (
    <section className="card">
      <h2>Notes due <span className="muted small">· review within 7 days</span></h2>
      <ul className="notes-due">
        {notes.map((n) => (
          <li key={n.id}>
            <div className="row" style={{ gap: 8 }}>
              <Link to={`/t/${n.symbol}`} className="sym">{n.symbol}</Link>
              {!n.held && (
                <span className="tag" title={n.lists.length ? `On ${n.lists.join(", ")}` : undefined}>
                  not held{portfolio === ALL ? "" : ` in ${portfolio}`}{n.lists.length ? ` · ${n.lists.join(", ")}` : ""}
                </span>
              )}
              <span className={`small ${n.review_on! < today ? "down" : "muted"}`}>
                {n.review_on! < today ? "overdue since" : n.review_on === today ? "due today" : "due"}{n.review_on === today ? "" : ` ${day(n.review_on!)}`}
              </span>
              {n.kind === "thesis" && <span className="muted small">thesis</span>}
            </div>
            <p className="small notes-due-text" title={n.text}>{n.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
