from datetime import date
from lib.storage import (
    read_transactions,
    write_transactions,
    append_transactions,
    update_transaction,
    get_statement_period,
    get_transactions_for_statement_period,
)


def test_read_write_transactions(dynamodb_mock, env_setup):
    txns = [
        {"transaction_id": "1", "amount": "10.00", "merchant": "Test"},
        {"transaction_id": "2", "amount": "20.00", "merchant": "Test2"},
    ]
    write_transactions(txns)

    read_back = read_transactions()
    assert len(read_back) == 2
    assert read_back[0]["transaction_id"] == "1"
    assert read_back[1]["amount"] == "20.00"


def test_append_transactions_no_duplicates(dynamodb_mock, env_setup):
    initial = [{"transaction_id": "1", "amount": "10.00"}]
    write_transactions(initial)

    new_txns = [
        {"transaction_id": "1", "amount": "10.00"},  # Duplicate
        {"transaction_id": "2", "amount": "20.00"},  # New
    ]

    added_count = append_transactions(new_txns)
    assert added_count == 1

    final_list = read_transactions()
    assert len(final_list) == 2
    ids = [t["transaction_id"] for t in final_list]
    assert "1" in ids
    assert "2" in ids


def test_update_transaction(dynamodb_mock, env_setup):
    initial = [{"transaction_id": "1", "classification": ""}]
    write_transactions(initial)

    success = update_transaction("1", "S", "Alex", 50)
    assert success is True

    updated = read_transactions()[0]
    assert updated["classification"] == "S"
    assert updated["classified_by"] == "Alex"
    assert updated["percentage"] == "50"


def test_update_transaction_already_classified(dynamodb_mock, env_setup):
    initial = [{"transaction_id": "1", "classification": "A"}]
    write_transactions(initial)

    success = update_transaction("1", "B", "Beth", None)
    assert success is False  # Should fail if already classified

    # Ensure it didn't change
    stored = read_transactions()[0]
    assert stored["classification"] == "A"


def test_statement_period_calculation():
    # Settlement date: Feb 1st -> Jan statement (Dec 10 - Jan 9)
    start, end = get_statement_period(date(2026, 2, 1))
    assert start == date(2025, 12, 10)
    assert end == date(2026, 1, 9)

    # Settlement date: Jan 1st -> Dec statement (Nov 10 - Dec 9)
    start, end = get_statement_period(date(2026, 1, 1))
    assert start == date(2025, 11, 10)
    assert end == date(2025, 12, 9)


def test_get_transactions_for_statement(dynamodb_mock, env_setup):
    txns = [
        {"transaction_id": "1", "date": "2025-12-09"},  # In range
        {"transaction_id": "2", "date": "2025-12-10"},  # In range
        {"transaction_id": "3", "date": "2026-01-09"},  # In range
        {"transaction_id": "4", "date": "2026-01-10"},  # Out range (next)
        {
            "transaction_id": "5",
            "date": "2025-12-09",
        },  # Out range (prev? No, wait. 12-10 start. So 12-09 is prev statement)
    ]
    # Wait, check logic:
    # Period: Dec 10 - Jan 9.
    # 2025-12-09 is BEFORE Dec 10. So it belongs to Nov 10-Dec 9 cycle.

    write_transactions(txns)

    # Settlement Feb 1st (for Jan statement: Dec 10 - Jan 9)
    filtered = get_transactions_for_statement_period(date(2026, 2, 1))

    ids = [t["transaction_id"] for t in filtered]
    assert "2" in ids  # Dec 10
    assert "3" in ids  # Jan 9
    assert "1" not in ids  # Dec 9 (too early)
    assert "4" not in ids  # Jan 10 (too late)
