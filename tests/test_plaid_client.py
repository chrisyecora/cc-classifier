from lib.plaid_client import fetch_new_transactions

# Mock data
SAMPLE_PLAID_TRANSACTIONS = [
    {
        "transaction_id": "tx1",
        "date": "2026-01-29",
        "amount": 50.00,
        "name": "Target",
        "merchant_name": "Target"
    },
    {
        "transaction_id": "tx2",
        "date": "2026-01-28",
        "amount": -10.00, # Credit
        "name": "Refund",
        "merchant_name": "Target"
    }
]

def test_fetch_new_transactions_success(mocker, env_setup):
    # Mock Plaid API client
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Mock transactions_sync response
    mock_response = mocker.MagicMock()
    mock_response.to_dict.return_value = {
        "added": SAMPLE_PLAID_TRANSACTIONS,
        "modified": [],
        "removed": [],
        "has_more": False,
        "next_cursor": "new_cursor"
    }
    # Direct attribute access for Plaid models
    mock_response.added = SAMPLE_PLAID_TRANSACTIONS
    mock_response.has_more = False
    mock_response.next_cursor = "new_cursor"
    
    mock_client.transactions_sync.return_value = mock_response
    
    txns, modified, removed, cursor = fetch_new_transactions("old_cursor")
    
    # Should transform data and sort (tx2 is older than tx1, so tx2 should be first)
    assert len(txns) == 2
    assert txns[0]["transaction_id"] == "tx1"
    assert txns[1]["transaction_id"] == "tx2"
    assert cursor == "new_cursor"
    
    # Verify API call
    mock_client.transactions_sync.assert_called_once()

def test_fetch_new_transactions_retry_logic(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Fail twice, then succeed
    mock_response = mocker.MagicMock()
    mock_response.added = []
    mock_response.has_more = False
    mock_response.next_cursor = "c"
    
    from plaid.exceptions import ApiException
    mock_client.transactions_sync.side_effect = [
        ApiException("error"),
        ApiException("error"),
        mock_response
    ]
    
    # Mock time.sleep to speed up test
    mocker.patch("time.sleep")
    
    fetch_new_transactions("c")
    
    assert mock_client.transactions_sync.call_count == 3
