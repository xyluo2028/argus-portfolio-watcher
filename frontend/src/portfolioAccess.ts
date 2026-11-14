import { createContext, useContext } from "react";
import type { PortfolioRef } from "./api";

/** Who shared the selected portfolio with you (null: it's yours, or "all"). Pages hide their write
 * controls for a shared portfolio: the server refuses those writes anyway (READ_ONLY). */
export const SharedBy = createContext<string | null>(null);
export const useSharedBy = () => useContext(SharedBy);

/** How the picker and the API refer to a portfolio: your own by name, a shared one by id (its name
 * may match one of yours, and a name finds yours first). */
export const portfolioKey = (p: PortfolioRef) => (p.shared ? String(p.id) : p.name);
