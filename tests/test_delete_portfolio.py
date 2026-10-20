"""Deleting a whole portfolio: counts first, exact-name confirmation, backup, nothing else touched."""

import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from argus.api.server import create_app
from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import AuditLog, NavDaily, Target, Transaction
from argus.services.portfolio import TxnInput
from tests.conftest import FakeQuotes

T0 = datetime(2026, 9, 1, 15, tzinfo=UTC)


@pytest.fixture
def a(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "BBB": (50, 50), "SPY": (500, 495)})])
    for name in ("growth", "income"):
        a.portfolios.create_portfolio(name)
    a.portfolios.add_transactions("growth", [TxnInput(type="BUY", symbol="AAA", ts=T0, qty=10, price=90),
                                             TxnInput(type="BUY", symbol="BBB", ts=T0, qty=5, price=40)])
    a.portfolios.add_transactions("income", [TxnInput(type="BUY", symbol="BBB", ts=T0, qty=1, price=40)])
    sell = a.portfolios.add_transactions("growth", [TxnInput(type="SELL", symbol="BBB", ts=T0, qty=5, price=45)])
    a.portfolios.delete_transaction(sell["inserted_ids"][0])  # soft-deleted rows go too
    a.set_targets("growth", "symbol", {"AAA": 60}, dry_run=False)
    return a


def _count(a, model, **where):
    with session_scope(a.engine) as s:
        q = select(func.count()).select_from(model)
        for k, v in where.items():
            q = q.where(getattr(model, k) == v)
        return s.scalar(q)


def test_dry_run_counts_and_changes_nothing(a):
    d = a.delete_portfolio("growth")
    assert d["dry_run"] and d["counts"] == {"transactions": 3, "targets": 1, "nav_days": 0, "open_positions": 2}
    assert [p["name"] for p in a.portfolios.list_portfolios()] == ["growth", "income"]


def test_delete_needs_the_exact_name_then_backs_up_and_removes_only_that_portfolio(a, settings):
    gid = a.portfolios.get_portfolio("growth").id
    with session_scope(a.engine) as s:
        s.add(NavDaily(portfolio_id=gid, d=T0.date(), market_value=1000.0))
    for wrong in (None, "Growth", "income"):
        with pytest.raises(ArgusError) as e:
            a.delete_portfolio("growth", confirm=wrong, dry_run=False)
        assert e.value.code == "INVALID_ARG"
    assert _count(a, Transaction, portfolio_id=gid) == 3

    revision = a.portfolios.revision
    d = a.delete_portfolio("growth", confirm="growth", dry_run=False, actor="ui")
    assert d["counts"]["nav_days"] == 1 and a.portfolios.revision > revision
    assert [p["name"] for p in a.portfolios.list_portfolios()] == ["income"]
    assert (_count(a, Transaction, portfolio_id=gid), _count(a, Target, portfolio_id=gid),
            _count(a, NavDaily, portfolio_id=gid)) == (0, 0, 0)
    assert _count(a, Transaction) == 1  # income's trade stays
    with session_scope(a.engine) as s:
        log = s.scalar(select(AuditLog).where(AuditLog.entity == "portfolio", AuditLog.action == "delete"))
        assert (log.actor, log.before["name"], log.before["counts"]["transactions"]) == ("ui", "growth", 3)

    # The backup holds everything as it was, so a full restore brings growth back.
    backup = json.loads(open(d["backup"]).read())
    assert {p["name"] for p in backup["tables"]["portfolio"]} == {"growth", "income"}
    a.snapshots.restore(backup, replace=True, dry_run=False)
    assert [p["name"] for p in a.portfolios.list_portfolios()] == ["growth", "income"]


def test_delete_endpoint_previews_by_default(a):
    with TestClient(create_app(a, start_hub=False), base_url="http://localhost") as c:
        r = c.delete("/api/portfolios/growth")
        assert r.status_code == 200 and r.json()["dry_run"] and r.json()["counts"]["transactions"] == 3
        r = c.delete("/api/portfolios/growth?dry_run=false&confirm=nope")
        assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_ARG"
        r = c.delete("/api/portfolios/growth?dry_run=false&confirm=growth")
        assert r.status_code == 200 and r.json()["backup"].endswith(".json")
        assert c.delete("/api/portfolios/growth").status_code == 404
        assert c.delete("/api/portfolios/all").status_code == 400  # the combined view isn't a portfolio


def test_cli_delete_prompts_for_the_name(a, monkeypatch):
    from typer.testing import CliRunner

    from argus import cli

    monkeypatch.setattr(cli, "_argus", lambda: a)
    runner = CliRunner()
    r = runner.invoke(cli.app, ["portfolio", "delete", "growth"], input="growt\n")
    assert r.exit_code == 1 and "Not deleted" in r.output
    r = runner.invoke(cli.app, ["portfolio", "delete", "growth", "--json"])
    assert r.exit_code == 1 and json.loads(r.output)["error"]["message"] == "Deleting needs --yes with --json."
    r = runner.invoke(cli.app, ["portfolio", "delete", "growth"], input="growth\n")
    assert r.exit_code == 0 and "Deleted growth" in r.output
    r = runner.invoke(cli.app, ["portfolio", "delete", "income", "--yes", "--json"])
    assert json.loads(r.output)["data"]["portfolio"]["name"] == "income"
    assert a.portfolios.list_portfolios() == []
