import pytest
from unittest.mock import MagicMock
from lib.storage import read_transactions, get_unclassified_transactions

def test_read_transactions_pagination(mocker, env_setup):
    # Mock the Table resource
    mock_table = MagicMock()
    mock_dynamodb = mocker.patch("boto3.resource")
    mock_dynamodb.return_value.Table.return_value = mock_table
    
    # Page 1: Returns 1 item + LastEvaluatedKey
    page1 = {
        "Items": [{"pk": "TRX", "sk": "1", "transaction_id": "1", "amount": "10"}],
        "LastEvaluatedKey": {"pk": "TRX", "sk": "1"}
    }
    
    # Page 2: Returns 1 item, no LastEvaluatedKey
    page2 = {
        "Items": [{"pk": "TRX", "sk": "2", "transaction_id": "2", "amount": "20"}]
    }
    
    mock_table.scan.side_effect = [page1, page2]
    
    # Run
    items = read_transactions()
    
    # Verify
    assert len(items) == 2
    assert items[0]["transaction_id"] == "1"
    assert items[1]["transaction_id"] == "2"
    assert mock_table.scan.call_count == 2
    
    # Verify second call used ExclusiveStartKey
    args, kwargs = mock_table.scan.call_args_list[1]
    assert kwargs["ExclusiveStartKey"] == {"pk": "TRX", "sk": "1"}

def test_get_unclassified_transactions_pagination(mocker, env_setup):
    mock_table = MagicMock()
    mock_dynamodb = mocker.patch("boto3.resource")
    mock_dynamodb.return_value.Table.return_value = mock_table
    
    # Page 1
    page1 = {
        "Items": [{"pk": "TRX", "sk": "1", "transaction_id": "1", "amount": "10"}],
        "LastEvaluatedKey": {"pk": "TRX", "sk": "1"}
    }
    
    # Page 2
    page2 = {
        "Items": [{"pk": "TRX", "sk": "2", "transaction_id": "2", "amount": "20"}]
    }
    
    mock_table.scan.side_effect = [page1, page2]
    
    items = get_unclassified_transactions()
    
    assert len(items) == 2
    assert items[0]["transaction_id"] == "1"
    assert items[1]["transaction_id"] == "2"
    assert mock_table.scan.call_count == 2
    
    args, kwargs = mock_table.scan.call_args_list[1]
    assert kwargs["ExclusiveStartKey"] == {"pk": "TRX", "sk": "1"}
