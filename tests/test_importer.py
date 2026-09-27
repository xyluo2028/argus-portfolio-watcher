import shutil
from datetime import date

import pytest

from argus.errors import ArgusError
from argus.importers.investing import parse_investing_csv, plan_transactions, reconcile
from tests.conftest import FIXTURES, FakeQuotes

SAMPLE = FIXTURES / "sample_Holdings_01152026.csv"


def test_parse_reads_only_lot_fields_and_name_from_filename():
    p = parse_investing_csv(SAMPLE)
    assert p.portfolio_name == "sample"
    assert [(l.symbol, l.qty, l.price) for l in p.lots][:2] == [("AAPL", 10, 170), ("AAPL", 5, 200)]
    assert p.lots[0].open_date == date(2026, 1, 2)
    assert p.summary["SPY"] == (2, 500)
    assert p.totals == {"Market Value": 4640.0, "Open P/L": 340.0}


def test_reconcile_passes_on_consistent_export():
    checks = {c["check"]: c for c in reconcile(parse_investing_csv(SAMPLE))}
    assert all(c["ok"] for c in checks.values()), checks
    assert set(checks) == {"long_only", "lots_match_summary", "total_cost"}


def test_reconcile_catches_tampered_lot(tmp_path):
    bad = tmp_path / "bad_Holdings_01152026.csv"
    bad.write_text(SAMPLE.read_text().replace('"5.00000000","200.00"', '"6.00000000","200.00"'))
    checks = {c["check"]: c for c in reconcile(parse_investing_csv(bad))}
    assert not checks["lots_match_summary"]["ok"] and "AAPL" in checks["lots_match_summary"]["detail"]
    assert not checks["total_cost"]["ok"]


def test_plan_classifies_opening_and_numbers_duplicate_lots():
    planned = plan_transactions(parse_investing_csv(SAMPLE), opening_through=date(2026, 1, 2))
    assert [t.type for t in planned] == ["OPENING", "BUY", "OPENING", "OPENING", "OPENING"]
    spy_ids = [t.external_id for t in planned if t.symbol == "SPY"]
    assert spy_ids[0] != spy_ids[1] and spy_ids[1].endswith(":2")


def test_import_end_to_end_is_idempotent(make_argus, tmp_path):
    a = make_argus([FakeQuotes("fake", {"AAPL": (200, 198), "KO": (62, 61), "SPY": (510, 505)})])
    dry = a.import_investing(SAMPLE, opening_through=date(2026, 1, 2), dry_run=True)
    assert dry["status"] == "ok" and dry["creates_portfolio"] and a.portfolios.list_portfolios() == []

    first = a.import_investing(SAMPLE, opening_through=date(2026, 1, 2), dry_run=False)
    assert first["inserted"] == 5
    again = a.import_investing(SAMPLE, opening_through=date(2026, 1, 2), dry_run=False)
    assert (again["inserted"], again["skipped_existing"]) == (0, 5)

    s = a.portfolio("sample")
    assert s["totals"]["cost_basis"] == pytest.approx(4300)
    assert s["totals"]["market_value"] == pytest.approx(4640)
    aapl = next(r for r in s["positions"] if r["symbol"] == "AAPL")
    assert aapl["avg_cost"] == pytest.approx(180) and aapl["lot_count"] == 2


def test_import_blocked_when_symbol_does_not_resolve(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAPL": (200, 198), "KO": (62, 61)})])  # no SPY
    report = a.import_investing(SAMPLE, dry_run=True)
    assert report["status"] == "blocked"
    with pytest.raises(ArgusError) as e:
        a.import_investing(SAMPLE, dry_run=False)
    assert e.value.code == "CHECKS_FAILED"


def test_missing_section_is_a_clear_error(tmp_path):
    f = tmp_path / "x_Holdings_01012026.csv"
    f.write_text('"Something else"\n"a","b"\n')
    with pytest.raises(ArgusError) as e:
        parse_investing_csv(f)
    assert e.value.code == "BAD_FORMAT"
