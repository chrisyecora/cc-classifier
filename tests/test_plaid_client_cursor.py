import pytest
from datetime import date, timedelta
from lib.plaid_client import fetch_new_transactions, get_plaid_client

# Helper to mock sync response
def mock_sync_response(mocker, client_mock, added=[], modified=[], removed=[], has_more=False, next_cursor="next"):
    mock_response = mocker.MagicMock()
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
    page1.to_dict.return_value = {
        "added": [{"transaction_id": "p1", "date": str(date.today()), "amount": 1}],
        "has_more": True,
        "next_cursor": "c1"
    }
    
    # Page 2: has_more = False
    page2 = mocker.MagicMock()
    page2.to_dict.return_value = {
        "added": [{"transaction_id": "p2", "date": str(date.today()), "amount": 2}],
        "has_more": False,
        "next_cursor": "c2"
    }
    
    mock_client.transactions_sync.side_effect = [page1, page2]
    
    transactions, new_cursor = fetch_new_transactions("start")
    
    assert len(transactions) == 2
    assert transactions[0]["transaction_id"] == "p1"
    assert transactions[1]["transaction_id"] == "p2"
    assert new_cursor == "c2"
    assert mock_client.transactions_sync.call_count == 2
