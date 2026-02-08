import pytest
from lib.storage import write_transactions, read_transactions, reset_transaction

def test_reset_transaction(s3_mock, env_setup):
    # Setup classified transaction
    initial = [{
        "transaction_id": "tx1", 
        "amount": "50.00", 
        "classification": "S", 
        "classified_by": "Chris", 
        "percentage": "50"
    }]
    write_transactions(initial)
    
    # Reset it
    success = reset_transaction("tx1")
    assert success is True
    
    # Verify cleared
    updated = read_transactions()[0]
    assert updated["classification"] == ""
    assert updated["classified_by"] == ""
    assert updated["percentage"] == ""
    assert updated["amount"] == "50.00" # Should preserve other fields

def test_reset_transaction_not_found(s3_mock, env_setup):
    success = reset_transaction("nonexistent")
    assert success is False
