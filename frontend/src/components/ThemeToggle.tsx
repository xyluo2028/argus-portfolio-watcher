import { useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
const NEXT: Record<Theme, Theme> = { system: "light", light: "dark", dark: "system" };
const KEY = "argus.theme";

function load(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system";
  }
}

export function applyStoredTheme() {
  const t = load();
  if (t !== "system") document.documentElement.dataset.theme = t;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(load);
  useEffect(() => {
    if (theme === "system") delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }
    window.dispatchEvent(new Event("argus-theme"));
  }, [theme]);
  return (
    <button className="btn" onClick={() => setTheme(NEXT[theme])} title="Theme">
      {theme === "system" ? "◐ Auto" : theme === "light" ? "☀ Light" : "☾ Dark"}
    </button>
  );
}
