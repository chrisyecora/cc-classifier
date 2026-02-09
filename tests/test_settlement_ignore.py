from datetime import date
from decimal import Decimal
from lib.settlement import calculate_settlement
from lib.storage import write_transactions

def test_settlement_ignores_excluded(dynamodb_mock, env_setup):
    # Setup transactions
    # 1. User A (included)
    # 2. Excluded (should be ignored)
    # 3. Unclassified (should be counted)
    
    txns = [
        {"transaction_id": "1", "date": "2025-12-15", "amount": "10.00", "merchant": "A", "classification": "A", "excluded": ""},
        {"transaction_id": "2", "date": "2025-12-16", "amount": "100.00", "merchant": "IgnoreMe", "classification": "", "excluded": "true"},
        {"transaction_id": "3", "date": "2025-12-17", "amount": "5.00", "merchant": "Unclassified", "classification": "", "excluded": ""}
    ]
    write_transactions(txns)
    
    # Settlement date Feb 1st covers Dec 10 - Jan 9
    result = calculate_settlement(date(2026, 2, 1))
    
    # User A should have 10.00
    assert result.user_a.total_owed == Decimal("10.00")
    
    # User B should have 0.00
    assert result.user_b.total_owed == Decimal("0.00")
    
    # Unclassified count should be 1 (txn 3), NOT 2 (txn 2 is excluded)
    assert result.unclassified_count == 1
