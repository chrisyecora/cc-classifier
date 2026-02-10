import pytest
from lib.storage import update_transaction_note, reset_transaction, read_transactions, write_transactions

def test_update_transaction_note(dynamodb_mock, env_setup):
    # Setup initial data
    initial = [{
        "transaction_id": "txn_123", 
        "amount": "100.00", 
        "merchant": "Test Merchant", 
        "classification": "S", 
        "classified_by": "UserA", 
        "percentage": "50",
        "notified_at": "2023-10-01",
        "note": ""
    }]
    write_transactions(initial)
    
    # Execute
    result = update_transaction_note("txn_123", "Business lunch")
    
    # Verify
    assert result is True
    
    # Check stored value
    updated = read_transactions()[0]
    assert updated["note"] == "Business lunch"

def test_reset_transaction_clears_note(dynamodb_mock, env_setup):
    # Setup initial data with a note
    initial = [{
        "transaction_id": "txn_123", 
        "amount": "100.00", 
        "merchant": "Test Merchant", 
        "classification": "S", 
        "classified_by": "UserA", 
        "percentage": "50",
        "notified_at": "2023-10-01",
        "note": "Old Note"
    }]
    write_transactions(initial)
    
    # Execute
    result = reset_transaction("txn_123")
    
    # Verify
    assert result is True
    
    # Check stored value
    updated = read_transactions()[0]
    assert updated.get("note") == "" or updated.get("note") is None
    assert updated.get("classification") == ""
    assert updated.get("classified_by") == ""