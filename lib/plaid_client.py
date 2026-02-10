import time
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from datetime import date, timedelta
from config import get_config

_client = None

def get_plaid_client():
    global _client
    if _client is None:
        config = get_config()
        # Handle Sandbox vs Production/Development
        # Plaid's python client uses specific Environment enums
        host = plaid.Environment.Sandbox
        if config.plaid_env == "production":
             host = plaid.Environment.Production
        elif config.plaid_env == "development":
             host = plaid.Environment.Development

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

def _transform_transactions(plaid_transactions: list) -> list[dict]:
    result = []
    for t in plaid_transactions:
        # Handle both dict and object (Plaid model)
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
            
        merchant_display = merchant_name if merchant_name else name
        
        result.append({
            "transaction_id": txn_id,
            "date": str(date_val),
            "amount": str(amount),
            "merchant": merchant_display, 
            "classification": "",
            "classified_by": "",
            "percentage": "",
            "notified_at": ""
        })
    return result


def fetch_new_transactions(cursor: str | None, max_retries: int = 3) -> tuple[list[dict], str]:
    """
    Fetches new transactions starting from the provided cursor.
    If cursor is None (initial sync), fetches all available history (up to Plaid's limit).
    Returns (transactions, new_cursor).
    """
    client = get_plaid_client()
    config = get_config()
    
    added_transactions = []
    current_cursor = cursor if cursor else ''
    has_more = True
    
    for attempt in range(max_retries):
        try:
            while has_more:
                request = TransactionsSyncRequest(
                    access_token=config.plaid_access_token,
                    cursor=current_cursor,
                    count=500
                )
                response = client.transactions_sync(request)
                
                added_transactions.extend(response.added)
                
                has_more = response.has_more
                current_cursor = response.next_cursor
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error fetching new transactions: {e}")
                raise e
            time.sleep(2 ** attempt)
    
    # Filter logic
    final_transactions = []
    
    if cursor is None:
        # Initial Sync: Keep only last 30 days
        cutoff = date.today() - timedelta(days=30)
        for t in added_transactions:
            # Handle both dict and object for date access
            if isinstance(t, dict):
                t_date_val = t.get('date')
            else:
                t_date_val = getattr(t, 'date', None)
                
            t_date_str = str(t_date_val)
            if not t_date_str: continue
            try:
                if date.fromisoformat(t_date_str) >= cutoff:
                    final_transactions.append(t)
            except ValueError: continue
    else:
        # Incremental Sync: Keep everything
        final_transactions = added_transactions
            
    # Transform
    return _transform_transactions(final_transactions), current_cursor
