"""Portfolio analysis: exposure (direct and ETF look-through), concentration, drift from
targets, and what-if trades. Pure functions over summary rows so they're easy to test.

Look-through uses each ETF's sector weights and its published top holdings (typically the
top 10), so indirect single-stock exposure is a floor, not the full amount.
"""

from __future__ import annotations

from collections import defaultdict

UNCLASSIFIED = "Unclassified"


def value(row: dict) -> float:
    """Market value, or cost basis when unpriced."""
    return row.get("market_value") if row.get("market_value") is not None else row.get("cost_basis", 0.0)


def is_fund(row: dict, profiles: dict[str, dict]) -> bool:
    return bool(profiles.get(row["symbol"], {}).get("sectors")) or row.get("sector") == "ETF" or row.get("type") == "ETP"


def concentration(values: list[float]) -> dict:
    total = sum(values)
    if total <= 0:
        return {}
    w = sorted((v / total for v in values), reverse=True)
    hhi = sum(x * x for x in w)
    return {"top1_pct": w[0] * 100, "top5_pct": sum(w[:5]) * 100, "top10_pct": sum(w[:10]) * 100,
            "hhi": hhi, "effective_positions": 1 / hhi if hhi else None, "positions": len(w)}


def exposure(rows: list[dict], profiles: dict[str, dict]) -> dict:
    total = sum(value(r) for r in rows)
    if total <= 0:
        return {"total_value": 0.0}
    direct: dict[str, float] = defaultdict(float)
    through: dict[str, float] = defaultdict(float)
    by_type: dict[str, float] = defaultdict(float)
    stock_exposure: dict[str, dict] = {}

    for r in rows:
        v = value(r)
        prof = profiles.get(r["symbol"], {})
        fund = is_fund(r, profiles)
        by_type["ETF" if fund else "Stock"] += v
        direct["ETF" if fund else (r.get("sector") or UNCLASSIFIED)] += v
        if fund and prof.get("sectors"):
            covered = sum(prof["sectors"].values())
            for sector, w in prof["sectors"].items():
                through[sector] += v * w
            if covered < 0.999:
                through[UNCLASSIFIED] += v * (1 - covered)
        else:
            through[UNCLASSIFIED if fund else (r.get("sector") or UNCLASSIFIED)] += v
        if not fund:
            e = stock_exposure.setdefault(r["symbol"], {"symbol": r["symbol"], "direct": 0.0, "via_etfs": 0.0, "via": []})
            e["direct"] += v
        for h in prof.get("top_holdings", []):
            sym = h["symbol"]
            e = stock_exposure.setdefault(sym, {"symbol": sym, "direct": 0.0, "via_etfs": 0.0, "via": []})
            e["via_etfs"] += v * h["weight"]
            e["via"].append(r["symbol"])
            e.setdefault("name", h.get("name"))

    def table(d: dict[str, float]) -> list[dict]:
        return [{"key": k, "value": v, "weight_pct": v / total * 100} for k, v in sorted(d.items(), key=lambda x: -x[1])]

    look = sorted(stock_exposure.values(), key=lambda e: -(e["direct"] + e["via_etfs"]))
    for e in look:
        e["total"] = e["direct"] + e["via_etfs"]
        e["total_pct"] = e["total"] / total * 100
    return {
        "total_value": total,
        "by_type": table(by_type),
        "by_sector_direct": table(direct),
        "by_sector_lookthrough": table(through),
        "concentration": concentration([value(r) for r in rows]),
        "top_stock_exposure": [e for e in look if e["via_etfs"] > 0 or e["direct"] > 0][:15],
        "funds_without_profile": [r["symbol"] for r in rows if is_fund(r, profiles) and not profiles.get(r["symbol"], {}).get("sectors")],
    }


def drift(rows: list[dict], targets: dict[str, float], level: str, tolerance_pp: float = 2.0) -> dict:
    """Current vs target weight per symbol or sector, with the $ trade that closes each gap."""
    total = sum(value(r) for r in rows)
    current: dict[str, float] = defaultdict(float)
    for r in rows:
        key = r["symbol"] if level == "symbol" else (r.get("sector") or UNCLASSIFIED)
        current[key] += value(r)
    keys = list(dict.fromkeys([*targets, *sorted(current, key=lambda k: -current[k])]))
    out = []
    for k in keys:
        cur_pct = current.get(k, 0.0) / total * 100 if total else 0.0
        tgt = targets.get(k)
        row = {"key": k, "value": current.get(k, 0.0), "weight_pct": cur_pct, "target_pct": tgt}
        if tgt is not None:
            row["drift_pp"] = cur_pct - tgt
            row["trade_to_target"] = (tgt - cur_pct) / 100 * total  # + buy, - sell
            row["outside_band"] = abs(cur_pct - tgt) > tolerance_pp
        out.append(row)
    target_sum = sum(targets.values())
    return {
        "level": level,
        "total_value": total,
        "tolerance_pp": tolerance_pp,
        "targets_sum_pct": target_sum,
        "untargeted_pct": sum(r["weight_pct"] for r in out if r["target_pct"] is None),
        "rows": out,
        "warnings": ([] if abs(target_sum - 100) <= 0.5 or not targets
                     else [f"targets sum to {target_sum:.1f}%, not 100%"]),
    }
