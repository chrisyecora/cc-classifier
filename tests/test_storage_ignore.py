import pytest
from lib.storage import (
    read_transactions,
    write_transactions,
    exclude_transaction,
    reset_transaction,
    get_unclassified_transactions
)

def test_exclude_transaction(s3_mock, env_setup):
    initial = [{"transaction_id": "1", "amount": "10.00", "merchant": "Test", "classification": ""}]
    write_transactions(initial)
    
    # Exclude it
    success = exclude_transaction("1")
    assert success is True
    
    # Check it's excluded
    stored = read_transactions()[0]
    assert stored["excluded"] == "true"
    
    # Should not be in unclassified list
    unclassified = get_unclassified_transactions()
    ids = [t["transaction_id"] for t in unclassified]
    assert "1" not in ids

def test_reset_transaction_clears_exclusion(s3_mock, env_setup):
    initial = [{"transaction_id": "1", "amount": "10.00", "classification": "", "excluded": "true"}]
    write_transactions(initial)
    
    # Reset it
    success = reset_transaction("1")
    assert success is True
    
    # Check it's back to normal
    stored = read_transactions()[0]
    assert stored["excluded"] == ""
    
    # Should be back in unclassified list
    unclassified = get_unclassified_transactions()
    ids = [t["transaction_id"] for t in unclassified]
    assert "1" in ids
