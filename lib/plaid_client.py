import time
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from datetime import date
from config import get_config

_client = None

def get_plaid_client():
    global _client
    if _client is None:
        config = get_config()
        print("DEBUG", config)

        host = plaid.Environment.Sandbox
        if config.plaid_env == "sandbox":
            host = plaid.Environment.Sandbox


        if config.plaid_env == "production":
            host = plaid.Environment.Production

        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': config.plaid_client_id,
                'secret': config.plaid_secret,
            }
        )
        api_client = plaid.ApiClient(configuration)
        _client = plaid_api.PlaidApi(api_client)
    return _client

def fetch_transactions(start_date: date, end_date: date, max_retries: int = 3) -> list[dict]:
    """
    Fetches transactions using Plaid's /transactions/sync endpoint.
    Filters the results to include only those within start_date and end_date (inclusive).
    """
    client = get_plaid_client()
    config = get_config()
    
    added_transactions = []
    
    # Retry logic wraps the entire sync process
    for attempt in range(max_retries):
        try:
            cursor = ''
            has_more = True
            current_added = []
            
            while has_more:
                request = TransactionsSyncRequest(
                    access_token=config.plaid_access_token,
                    cursor=cursor,
                )
                response = client.transactions_sync(request)
                
                # Convert to dict for easier handling of lists
                resp_dict = response.to_dict()
                
                current_added.extend(resp_dict['added'])
                # We ignore modified/removed for this simple implementation
                
                has_more = resp_dict['has_more']
                cursor = resp_dict['next_cursor']
                
            added_transactions = current_added
            break # Success
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error fetching transactions: {e}")
                raise e
            time.sleep(2 ** attempt) # Exponential backoff
            
    # Filter by date range
    filtered_transactions = []
    for t in added_transactions:
        # t is a dict from response.to_dict()
        t_date_str = str(t.get('date')) # Ensure string 'YYYY-MM-DD'
        if not t_date_str:
            continue
            
        try:
            t_date = date.fromisoformat(t_date_str)
            if start_date <= t_date <= end_date:
                filtered_transactions.append(t)
        except ValueError:
            continue
            
    return _transform_transactions(filtered_transactions)

def _transform_transactions(plaid_transactions: list) -> list[dict]:
    result = []
    for t in plaid_transactions:
        # Handle both object (from test mocks) and dict (from sync response)
        if isinstance(t, dict):
            txn_id = t.get("transaction_id")
            date_val = t.get("date")
            amount = t.get("amount")
            name = t.get("name")
            merchant_name = t.get("merchant_name")
        else:
            txn_id = getattr(t, "transaction_id", None)
            date_val = getattr(t, "date", None)
            amount = getattr(t, "amount", None)
            name = getattr(t, "name", None)
            merchant_name = getattr(t, "merchant_name", None)
        
        result.append({
            "transaction_id": txn_id,
            "date": str(date_val),
            "amount": str(amount),
            "merchant": merchant_name or name, # Fallback to name if merchant is null
            "classification": "",
            "classified_by": "",
            "percentage": "",
            "notified_at": ""
        })
    return result