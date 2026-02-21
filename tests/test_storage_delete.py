from lib.storage import write_transactions, read_transactions, delete_transaction, get_transaction


def test_delete_transaction(dynamodb_mock, env_setup):
    # Setup: Create a transaction
    txns = [
        {"transaction_id": "1", "amount": "10.00", "merchant": "Test"},
        {"transaction_id": "2", "amount": "20.00", "merchant": "Test2"},
    ]
    write_transactions(txns)

    # Verify creation
    assert len(read_transactions()) == 2
    assert get_transaction("1") is not None

    # Test Deletion
    success = delete_transaction("1")
    assert success is True

    # Verify Deletion
    remaining = read_transactions()
    assert len(remaining) == 1
    assert remaining[0]["transaction_id"] == "2"
    assert get_transaction("1") is None

    # Test Deletion of non-existent item (should probably return True or False depending on implementation,
    # but boto3 delete_item is idempotent and doesn't fail if item missing unless ConditionalCheck used)
    # Our implementation uses default delete_item which succeeds even if item missing.
    # However, I didn't add ConditionExpression="attribute_exists(pk)" in my implementation.
    # Let's check what I wrote. I wrote:
    # try: table.delete_item(...) return True
    # So it should return True.

    success = delete_transaction("999")
    assert success is True
