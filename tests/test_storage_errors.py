import pytest
import boto3
from lib.storage import (
    append_transactions,
    update_transaction,
    exclude_transaction,
    update_transaction_note,
    reset_transaction,
    delete_transaction,
    update_transaction_details,
    get_user_by_phone,
    get_other_user,
    get_cursor,
    save_cursor,
    get_transaction
)

def test_get_transaction_not_found(dynamodb_mock, env_setup):
    assert get_transaction("nonexistent") is None

def test_append_transactions_conditional_failure(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.meta.client.meta.region_name = 'us-east-1'
    
    mock_dynamodb_client = mocker.MagicMock()
    mock_dynamodb_client.exceptions.TransactionCanceledException = boto3.client('dynamodb', region_name='us-east-1').exceptions.TransactionCanceledException
    mock_dynamodb_client.exceptions.ConditionalCheckFailedException = boto3.client('dynamodb', region_name='us-east-1').exceptions.ConditionalCheckFailedException
    mock_dynamodb_client.transact_write_items.side_effect = mock_dynamodb_client.exceptions.TransactionCanceledException(
        error_response={'Error': {'Code': 'TransactionCanceledException', 'Message': 'Failure'}},
        operation_name='TransactWriteItems'
    )
    
    mock_table.put_item.side_effect = boto3.client('dynamodb', region_name='us-east-1').exceptions.ConditionalCheckFailedException(
        error_response={'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Failure'}},
        operation_name='PutItem'
    )
    
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    mocker.patch("boto3.client", return_value=mock_dynamodb_client)
    
    # Should catch the exception and return count 0
    txns = [{"transaction_id": "1", "amount": "10.00"}]
    assert append_transactions(txns) == 0

def test_update_transaction_conditional_failure(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.update_item.side_effect = boto3.client('dynamodb').exceptions.ConditionalCheckFailedException(
        error_response={'Error': {'Code': 'ConditionalCheckFailedException', 'Message': 'Failure'}},
        operation_name='UpdateItem'
    )
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    
    assert update_transaction("1", "S", "Alex", 50) is False

def test_exclude_transaction_exception(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.update_item.side_effect = Exception("General Error")
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert exclude_transaction("1") is False

def test_update_transaction_note_exception(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.update_item.side_effect = Exception("General Error")
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert update_transaction_note("1", "Note") is False

def test_reset_transaction_exception(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.update_item.side_effect = Exception("General Error")
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert reset_transaction("1") is False

def test_delete_transaction_exception(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.delete_item.side_effect = Exception("General Error")
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert delete_transaction("1") is False

def test_update_transaction_details_success(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert update_transaction_details("1", "10", "2023", "M", "N") is True
    mock_table.update_item.assert_called_once()

def test_update_transaction_details_exception(mocker, env_setup):
    mock_table = mocker.MagicMock()
    mock_table.update_item.side_effect = Exception("General Error")
    mocker.patch("lib.storage.get_table", return_value=mock_table)
    assert update_transaction_details("1", "10", "2023", "M", "N") is False

def test_get_user_by_phone():
    assert get_user_by_phone("123") is None

def test_get_other_user(mocker, env_setup):
    mock_users = {
        "user_a": {"name": "Alice"},
        "user_b": {"name": "Bob"}
    }
    mocker.patch("lib.storage.read_users", return_value=mock_users)
    assert get_other_user("user_a") == {"id": "user_b", "name": "Bob"}
    assert get_other_user("user_b") == {"id": "user_a", "name": "Alice"}
    
def test_get_cursor_none(dynamodb_mock, env_setup):
    # Missing item
    assert get_cursor() is None

def test_save_cursor_empty():
    # Calling save_cursor with None/empty string should return early
    # It won't call table.put_item
    assert save_cursor("") is None
