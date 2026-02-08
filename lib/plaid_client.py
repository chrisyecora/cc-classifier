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
        env = plaid.Environment.Sandbox
        if config.environment == "prod":
             env = plaid.Environment.Production
        elif config.environment == "development":
             env = plaid.Environment.Development

        configuration = plaid.Configuration(
            host=env,
            api_key={
                'clientId': config.plaid_client_id,
                'secret': config.plaid_secret,
            }
        )
        api_client = plaid.ApiClient(configuration)
        _client = plaid_api.PlaidApi(api_client)
    return _client

def fetch_transactions(start_date: date, end_date: date, max_retries: int = 3) -> list[dict]:
    # Deprecated: Kept for backward compat / manual runs if needed, or redirect to new logic?
    # For now, let's keep it but rely on fetch_new_transactions for the main flow.
    # Actually, let's just make it a wrapper around fetch_new_transactions if possible? 
    # No, date filtering is specific.
    # We will leave this for 'backfill' command usage and add the new one.
    
    # ... existing implementation (simplified for brevity, assume unchanged) ...
    pass 
    # (Actually I need to keep the code if I want it to work for backfill command)
    # I will paste the full file content with the new function added.
    return []

# --- Re-implementing existing fetch_transactions for backfill support ---
def fetch_transactions(start_date: date, end_date: date, max_retries: int = 3) -> list[dict]:
    client = get_plaid_client()
    config = get_config()
    
    # We use sync but filter results since /transactions/get is deprecated/removed in some contexts
    # or we just iterate.
    # Actually, the previous implementation used Sync loop.
    
    added_transactions = []
    
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
                resp_dict = response.to_dict()
                current_added.extend(resp_dict['added'])
                has_more = resp_dict['has_more']
                cursor = resp_dict['next_cursor']
                
            added_transactions = current_added
            break 
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)

    # Filter
    filtered = []
    for t in added_transactions:
        t_date_str = str(t.get('date'))
        if not t_date_str: continue
        try:
            t_date = date.fromisoformat(t_date_str)
            if start_date <= t_date <= end_date:
                filtered.append(t)
        except ValueError: continue
            
    return _transform_transactions(filtered)


def fetch_new_transactions(cursor: str | None, max_retries: int = 3) -> tuple[list[dict], str]:
    """
    Fetches new transactions using the provided cursor.
    If cursor is None (initial sync), fetches all but filters to last 30 days.
    Returns (transactions, new_cursor).
    """
    client = get_plaid_client()
    config = get_config()
    
    added_transactions = []
    new_cursor = cursor
    
    # If no cursor, we start from beginning
    current_cursor = cursor if cursor else ''
    
    for attempt in range(max_retries):
        try:
            has_more = True
            current_added = []
            
            while has_more:
                request = TransactionsSyncRequest(
                    access_token=config.plaid_access_token,
                    cursor=current_cursor,
                )
                response = client.transactions_sync(request)
                resp_dict = response.to_dict()
                
                current_added.extend(resp_dict['added'])
                
                has_more = resp_dict['has_more']
                current_cursor = resp_dict['next_cursor']
            
            added_transactions = current_added
            new_cursor = current_cursor
            break
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error fetching transactions: {e}")
                raise e
            time.sleep(2 ** attempt)
            
    # Filter logic
    final_transactions = []
    
    if cursor is None:
        # Initial Sync: Keep only last 30 days
        cutoff = date.today() - timedelta(days=30)
        for t in added_transactions:
            t_date_str = str(t.get('date'))
            if not t_date_str: continue
            try:
                if date.fromisoformat(t_date_str) >= cutoff:
                    final_transactions.append(t)
            except ValueError: continue
    else:
        # Incremental Sync: Keep everything
        final_transactions = added_transactions
        
    return _transform_transactions(final_transactions), new_cursor

def _transform_transactions(plaid_transactions: list) -> list[dict]:
    result = []
    for t in plaid_transactions:
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
            "merchant": merchant_name or name, 
            "classification": "",
            "classified_by": "",
            "percentage": "",
            "notified_at": ""
        })
    return result