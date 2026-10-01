import json
from datetime import UTC, date, datetime

import pytest

from argus.app import Argus
from argus.config import Settings
from argus.errors import ArgusError
from argus.services.portfolio import TxnInput


def _settings(d):
    return Settings(data_dir=d, db_path=d / "argus.sqlite", finnhub_api_key=None, sec_user_agent=None)


def _seed(a):
    a.portfolios.create_portfolio("growth")
    ids = a.portfolios.add_transactions("growth", [
        TxnInput("OPENING", "NVDA", datetime(2026, 8, 25, 20, tzinfo=UTC), 50, 61.15),
        TxnInput("BUY", "AMD", datetime(2026, 9, 3, 15, tzinfo=UTC), 10, 150, external_id="k1"),
    ])["inserted_ids"]
    a.portfolios.delete_transaction(ids[1])
    a.notes.add("NVDA", "AI capex cycle", kind="thesis", review_on=date(2026, 11, 20))
    a.alerts.create("NVDA", "day_move_pct", 5)


def test_snapshot_roundtrip_into_fresh_instance(make_argus, tmp_path):
    src = make_argus()
    _seed(src)
    file = tmp_path / "snap.json"
    assert src.snapshots.dump(file)["counts"]["txn"] == 2
    assert json.loads(file.read_text())["format"] == "argus-snapshot"

    dst = Argus(_settings(tmp_path / "other"))
    assert dst.snapshots.load(file)["dry_run"]  # dry run by default
    assert dst.portfolios.list_portfolios() == []
    dst.snapshots.load(file, dry_run=False)

    assert dst.portfolios.positions("growth")["NVDA"].qty == 50
    all_txns = dst.portfolios.list_transactions("growth", include_deleted=True)
    assert [t["deleted"] for t in all_txns] == [False, True] and all_txns[1]["external_id"] == "k1"
    assert dst.notes.list("NVDA")[0]["review_on"] == "2026-11-20"
    assert dst.snapshots.counts() == src.snapshots.counts()


def test_snapshot_load_refuses_to_merge_unless_replace(make_argus, tmp_path):
    src = make_argus()
    _seed(src)
    file = tmp_path / "snap.json"
    src.snapshots.dump(file)

    dst = Argus(_settings(tmp_path / "other"))
    dst.portfolios.create_portfolio("scratch")
    with pytest.raises(ArgusError) as e:
        dst.snapshots.load(file, dry_run=False)
    assert e.value.code == "ALREADY_EXISTS"
    r = dst.snapshots.load(file, replace=True, dry_run=False)
    assert r["will_remove"] == {"portfolio": 1}
    assert [p["name"] for p in dst.portfolios.list_portfolios()] == ["growth"]


def test_snapshot_rejects_other_files(make_argus, tmp_path):
    bad = tmp_path / "x.json"
    bad.write_text('{"hello": 1}')
    with pytest.raises(ArgusError):
        make_argus().snapshots.load(bad)
