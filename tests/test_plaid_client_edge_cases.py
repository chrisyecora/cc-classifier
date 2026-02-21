from datetime import date
from lib.plaid_client import (
    get_plaid_client,
    _transform_transactions,
    fetch_new_transactions
)
import lib.plaid_client

def test_get_plaid_client_env_routing(mocker, env_setup):
    # Reset singleton
    lib.plaid_client._client = None
    
    mock_config = mocker.patch("lib.plaid_client.get_config")
    mock_config.return_value.plaid_env = "production"
    mock_config.return_value.plaid_client_id = "client"
    mock_config.return_value.plaid_secret = "secret"
    
    mocker.patch("plaid.ApiClient")
    mocker.patch("plaid.api.plaid_api.PlaidApi")
    
    client1 = get_plaid_client()
    assert client1 is not None
    
    # Check that it cached the client
    client2 = get_plaid_client()
    assert client1 is client2
    
    # Test dev env
    lib.plaid_client._client = None
    mock_config.return_value.plaid_env = "development"
    # Mock plaid.Environment since it doesn't have Development
    mocker.patch("plaid.Environment.Development", "mock_dev_env", create=True)
    get_plaid_client()

def test_transform_transactions_object_model():
    class MockTransaction:
        def __init__(self, tid, ptid, dt, amt, name, merchant):
            self.transaction_id = tid
            self.pending_transaction_id = ptid
            self.date = dt
            self.amount = amt
            self.name = name
            self.merchant_name = merchant
    
    txn_obj = MockTransaction("1", "p1", "2023-01-01", 10.0, "Test Name", "Test Merchant")
    
    result = _transform_transactions([txn_obj])
    assert len(result) == 1
    assert result[0]["transaction_id"] == "1"
    assert result[0]["amount"] == "10.0"
    assert result[0]["merchant"] == "Test Merchant"

def test_fetch_new_transactions_object_filtering(mocker, env_setup):
    class MockTransaction:
        def __init__(self, tid, dt):
            self.transaction_id = tid
            self.date = dt
    
    class MockSyncResponse:
        def __init__(self, added, modified, removed):
            self.added = added
            self.modified = modified
            self.removed = removed
            self.has_more = False
            self.next_cursor = "next"
            
    recent_date = str(date.today())
    # Object with valid date
    t_add = MockTransaction("1", recent_date)
    # Object with invalid date format to trigger ValueError in is_recent
    t_mod = MockTransaction("2", "not-a-date")
    # Object with None date to trigger the `if not t_date_str` implicitly or handle it
    t_add2 = MockTransaction("3", None)
    
    t_rem = MockTransaction("4", recent_date)
    
    mock_resp = MockSyncResponse([t_add, t_add2], [t_mod], [t_rem])
    
    mock_client = mocker.MagicMock()
    mock_client.transactions_sync.return_value = mock_resp
    mocker.patch("lib.plaid_client.get_plaid_client", return_value=mock_client)
    
    # Initial sync
    added, modified, removed, next_cur = fetch_new_transactions(None)
    
    assert len(added) == 1
    assert added[0]["transaction_id"] == "1"
    
    assert len(modified) == 0 # "not-a-date" filtered out
    
    assert len(removed) == 1
    assert removed[0]["transaction_id"] == "4"
