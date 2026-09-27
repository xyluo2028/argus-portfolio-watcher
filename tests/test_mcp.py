import asyncio
import json
from datetime import UTC, datetime

import pytest

from argus.mcp_server import create_mcp
from argus.services.portfolio import TxnInput
from tests.conftest import FakeQuotes


def call(mcp, name, args=None):
    res = asyncio.run(mcp.call_tool(name, args or {}))
    assert len(res.content) == 1 and "\n" not in res.content[0].text  # one compact JSON block
    return json.loads(res.content[0].text)


@pytest.fixture
def mcp(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "SPY": (500, 495)})])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "AAA", datetime(2026, 9, 1, 20, tzinfo=UTC), 10, 90)])
    return create_mcp(a)


def test_tools_are_listed_with_read_only_hints(mcp):
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert {"get_portfolio", "get_quotes", "add_transaction", "get_performance", "compare_symbols"} <= set(tools)
    assert tools["get_portfolio"].annotations.read_only_hint is True
    assert tools["delete_transaction"].annotations.destructive_hint is True
    props = tools["add_transaction"].input_schema["properties"]
    assert props["dry_run"]["default"] is True and "idempotency_key" in props


def test_get_portfolio_via_mcp(mcp):
    out = call(mcp, "get_portfolio", {"portfolio": "growth"})
    assert out["totals"]["market_value"] == 1100 and out["positions"][0]["symbol"] == "AAA"


def test_add_transaction_defaults_to_dry_run_then_commits_idempotently(mcp):
    args = {"portfolio": "growth", "type": "BUY", "symbol": "AAA", "qty": 5, "price": 100,
            "date": "2026-09-02", "idempotency_key": "k1"}
    preview = call(mcp, "add_transaction", args)
    assert preview["dry_run"] is True and preview["positions"][0]["after"]["qty"] == 15
    assert len(call(mcp, "list_transactions", {"portfolio": "growth"})) == 1
    saved = call(mcp, "add_transaction", args | {"dry_run": False})
    again = call(mcp, "add_transaction", args | {"dry_run": False})
    assert saved["inserted_ids"] and again["skipped_existing"] == ["k1"]
    txns = call(mcp, "list_transactions", {"portfolio": "growth"})
    assert len(txns) == 2 and txns[-1]["source"] == "mcp"


def test_errors_carry_code_and_hint(mcp):
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match=r"INSUFFICIENT_SHARES: .*\(hint: "):
        asyncio.run(mcp.call_tool("add_transaction", {"portfolio": "growth", "type": "SELL", "symbol": "AAA",
                                                       "qty": 99, "price": 1, "dry_run": False}))


def test_routine_tools(mcp):
    a = call(mcp, "set_alert", {"symbol": "AAA", "kind": "day_gain_pct", "threshold": 5})
    listed = call(mcp, "list_alerts", {"fired_since": "2000-01-01"})
    assert listed["alerts"][0]["id"] == a["id"] and listed["fired"][0]["symbol"] == "AAA"
    n = call(mcp, "add_note", {"symbol": "AAA", "text": "why I own it", "kind": "thesis", "review_on": "2000-01-01"})
    assert call(mcp, "list_notes", {"due_within_days": 0})[0]["id"] == n["id"]
    brief = call(mcp, "get_daily_brief_data", {"portfolio": "growth", "include_news": False})
    assert brief["top_gainers"][0]["symbol"] == "AAA" and brief["theses_due"]
    prompts = {p.name for p in asyncio.run(mcp.list_prompts())}
    assert {"daily_brief", "position_review"} <= prompts


def test_analysis_tools(mcp):
    e = call(mcp, "get_exposure", {"portfolio": "growth"})
    assert e["concentration"]["positions"] == 1
    sim = call(mcp, "simulate_trades", {"portfolio": "growth", "trades": [{"symbol": "AAA", "side": "SELL", "qty": 5}]})
    assert sim["saved"] is False and sim["net_cash"] == 550
    prev = call(mcp, "set_targets", {"portfolio": "growth", "level": "symbol", "weights": {"AAA": 100}})
    assert prev["dry_run"] is True
    assert call(mcp, "get_drift", {"portfolio": "growth"})["rows"][0]["target_pct"] is None  # not saved
