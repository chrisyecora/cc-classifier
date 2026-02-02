import time
import plaid
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from datetime import date
from config import get_config

_client = None

def get_plaid_client():
    global _client
    if _client is None:
        config = get_config()
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox if config.environment == "dev" else plaid.Environment.Production,
            api_key={
                'clientId': config.plaid_client_id,
                'secret': config.plaid_secret,
            }
        )
        api_client = plaid.ApiClient(configuration)
        _client = plaid_api.PlaidApi(api_client)
    return _client

def fetch_transactions(start_date: date, end_date: date, max_retries: int = 3) -> list[dict]:
    client = get_plaid_client()
    config = get_config()
    
    request = TransactionsGetRequest(
        access_token=config.plaid_access_token,
        start_date=start_date,
        end_date=end_date,
        options=TransactionsGetRequestOptions(
            count=500, # Max per page
            offset=0
        )
    )
    
    response = None
    for attempt in range(max_retries):
        try:
            response = client.transactions_get(request)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt) # Exponential backoff
            
    if not response:
        return []
        
    return _transform_transactions(response.transactions)

def _transform_transactions(plaid_transactions: list) -> list[dict]:
    result = []
    for t in plaid_transactions:
        # Access attributes directly assuming model object, but tests might use dicts if not careful.
        # Plaid-python returns model objects.
        # t.amount is positive for expenses in Plaid?
        # Plaid docs: "positive values when money moves out of the account" (Expense)
        # "negative values when money moves in" (Credit)
        
        # We handle credits (negative amounts) same as expenses for now, 
        # allowing classification of refunds.
        
        # Safe attribute access (handle mock objects which might be dicts in some test setups, 
        # but in our test we set `mock_response.transactions = [dict]`.
        # Real Plaid client returns objects. Our code should handle objects.
        # For our test to pass with dicts in `mock_response`, we'd need to mock them as objects 
        # or access them in a way that handles both.
        # Ideally, we should mock them as objects or use `getattr`.
        
        txn_id = getattr(t, "transaction_id", None) or t.get("transaction_id")
        date_val = getattr(t, "date", None) or t.get("date")
        amount = getattr(t, "amount", None) if hasattr(t, "amount") else t.get("amount")
        name = getattr(t, "name", None) or t.get("name")
        merchant_name = getattr(t, "merchant_name", None) or t.get("merchant_name")
        
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
