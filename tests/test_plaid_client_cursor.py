import pytest
from datetime import date, timedelta
from lib.plaid_client import fetch_new_transactions, get_plaid_client

# Helper to mock sync response
def mock_sync_response(mocker, client_mock, added=[], modified=[], removed=[], has_more=False, next_cursor="next"):
    mock_response = mocker.MagicMock()
    # Support both attribute access and to_dict (if used elsewhere, though new code uses attributes)
    mock_response.added = added
    mock_response.modified = modified
    mock_response.removed = removed
    mock_response.has_more = has_more
    mock_response.next_cursor = next_cursor
    
    mock_response.to_dict.return_value = {
        "added": added,
        "modified": modified,
        "removed": removed,
        "has_more": has_more,
        "next_cursor": next_cursor
    }
    client_mock.transactions_sync.return_value = mock_response

def test_fetch_new_transactions_with_cursor(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Mock data (old transaction, but since cursor is provided, we keep it)
    old_date = (date.today() - timedelta(days=100)).isoformat()
    # Plaid returns objects usually, but we use dicts in tests often.
    # The code converts them using getattr or get.
    # So using dicts here is fine given _transform_transactions implementation.
    txns_data = [{"transaction_id": "t1", "date": old_date, "amount": 10, "merchant_name": "Old"}]
    
    mock_sync_response(mocker, mock_client, added=txns_data, next_cursor="new_cursor")
    
    # Call with existing cursor
    transactions, new_cursor = fetch_new_transactions("old_cursor")
    
    assert len(transactions) == 1
    assert transactions[0]["transaction_id"] == "t1"
    assert new_cursor == "new_cursor"
    
    # Verify cursor was passed to API
    args, _ = mock_client.transactions_sync.call_args
    assert args[0].cursor == "old_cursor"

def test_fetch_new_transactions_initial_sync_filtering(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    today = date.today()
    old_date = (today - timedelta(days=40)).isoformat() # Should be filtered out
    recent_date = (today - timedelta(days=5)).isoformat() # Should be kept
    
    txns_data = [
        {"transaction_id": "t_old", "date": old_date, "amount": 10, "merchant_name": "Old"},
        {"transaction_id": "t_new", "date": recent_date, "amount": 20, "merchant_name": "New"}
    ]
    
    mock_sync_response(mocker, mock_client, added=txns_data, next_cursor="init_cursor")
    
    # Call with None cursor (Initial Sync)
    transactions, new_cursor = fetch_new_transactions(None)
    
    assert len(transactions) == 1
    assert transactions[0]["transaction_id"] == "t_new" # Only recent kept
    assert new_cursor == "init_cursor" # But we get the latest cursor

def test_pagination(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Page 1: has_more = True
    page1 = mocker.MagicMock()
    page1.added = [{"transaction_id": "p1", "date": str(date.today()), "amount": 1}]
    page1.has_more = True
    page1.next_cursor = "c1"
    
    # Page 2: has_more = False
    page2 = mocker.MagicMock()
    page2.added = [{"transaction_id": "p2", "date": str(date.today()), "amount": 2}]
    page2.has_more = False
    page2.next_cursor = "c2"
    
    mock_client.transactions_sync.side_effect = [page1, page2]
    
    transactions, new_cursor = fetch_new_transactions("start")
    
    assert len(transactions) == 2
    assert transactions[0]["transaction_id"] == "p1"
    assert transactions[1]["transaction_id"] == "p2"
    assert new_cursor == "c2"
    assert mock_client.transactions_sync.call_count == 2