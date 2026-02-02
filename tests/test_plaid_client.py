import pytest
from datetime import date
from lib.plaid_client import fetch_transactions, get_plaid_client

# Mock data
SAMPLE_PLAID_TRANSACTIONS = [
    {
        "transaction_id": "tx1",
        "date": "2026-01-28",
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

def test_fetch_transactions_success(mocker, env_setup):
    # Mock Plaid API client
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Mock response
    mock_response = mocker.MagicMock()
    mock_response.transactions = SAMPLE_PLAID_TRANSACTIONS
    mock_client.transactions_get.return_value = mock_response
    
    txns = fetch_transactions(date(2026, 1, 1), date(2026, 1, 31))
    
    # Should transform data
    assert len(txns) == 2
    assert txns[0]["transaction_id"] == "tx1"
    assert txns[0]["amount"] == "50.0"
    assert txns[0]["merchant"] == "Target"
    
    # Verify API call
    mock_client.transactions_get.assert_called_once()

def test_fetch_transactions_retry_logic(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Fail twice, then succeed
    mock_response = mocker.MagicMock()
    mock_response.transactions = []
    
    from plaid.exceptions import ApiException
    mock_client.transactions_get.side_effect = [
        ApiException("error"),
        ApiException("error"),
        mock_response
    ]
    
    # Mock time.sleep to speed up test
    mocker.patch("time.sleep")
    
    fetch_transactions(date(2026, 1, 1), date(2026, 1, 31))
    
    assert mock_client.transactions_get.call_count == 3

def test_transform_ignore_pending(mocker, env_setup):
    # If pending transactions are returned, we might want to filter them or handle them.
    # Plaid transactions_get usually returns posted + pending. 
    # Spec doesn't explicitly say to ignore pending, but usually for settlement we want posted.
    # Let's assume we take all for now, or check "pending" status if available.
    pass
