from datetime import date

import pytest

from lib.statements import ConflictError, save_period, statement_view
from lib.storage import get_transactions_between, write_transactions


def transaction(id, posted, amount="10.00", classification="A"):
    return {
        "transaction_id": id,
        "date": posted,
        "amount": amount,
        "merchant": id,
        "classification": classification,
        "excluded": "",
        "note": "",
    }


def test_confirmed_period_and_next_start(dynamodb_mock):
    write_transactions(
        [transaction("first", "2026-08-12"), transaction("last", "2026-09-09"), transaction("next", "2026-09-10")]
    )
    view = save_period("2026-09", "2026-08-12", "2026-09-09", 0)
    assert view["confirmed"]
    assert [item["transaction_id"] for item in view["transactions"]] == ["last", "first"]
    assert statement_view("2026-10")["start_date"] == "2026-09-10"
    assert len(get_transactions_between(date(2026, 8, 12), date(2026, 9, 9))) == 2


def test_period_overlap_and_stale_edit(dynamodb_mock):
    save_period("2026-09", "2026-08-12", "2026-09-09", 0)
    with pytest.raises(ValueError, match="overlaps"):
        save_period("2026-10", "2026-09-09", "2026-10-09", 0)
    with pytest.raises(ValueError, match="Start must follow"):
        save_period("2026-10", "2026-09-11", "2026-10-09", 0)
    with pytest.raises(ConflictError):
        save_period("2026-09", "2026-08-12", "2026-09-10", 0)
