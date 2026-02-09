import boto3
import csv
import io
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from config import get_config

# Constants
CSV_FIELDNAMES = [
    "transaction_id", "date", "amount", "merchant", 
    "classification", "classified_by", "percentage", "notified_at", "note", "excluded"
]
CSV_FILENAME = "transactions.csv"

def get_s3_client():
    return boto3.client("s3")

def read_transactions() -> list[dict]:
    config = get_config()
    s3 = get_s3_client()
    
    try:
        response = s3.get_object(Bucket=config.s3_bucket, Key=CSV_FILENAME)
        content = response["Body"].read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))
        return list(reader)
    except Exception as e:
        # Check if it's NoSuchKey. In boto3 it's a ClientError. 
        # For simplicity/mocking compat, if file missing return empty list
        if "NoSuchKey" in str(e):
            return []
        raise e

def write_transactions(transactions: list[dict]) -> None:
    config = get_config()
    s3 = get_s3_client()
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    writer.writerows(transactions)
    
    s3.put_object(
        Bucket=config.s3_bucket,
        Key=CSV_FILENAME,
        Body=output.getvalue(),
        ContentType="text/csv"
    )

def append_transactions(new_transactions: list[dict]) -> int:
    existing = read_transactions()
    existing_ids = {t["transaction_id"] for t in existing}
    
    to_add = []
    for txn in new_transactions:
        if txn["transaction_id"] not in existing_ids:
            # Ensure all fields present
            row = {k: txn.get(k, "") for k in CSV_FIELDNAMES}
            to_add.append(row)
            
    if to_add:
        # Combine and rewrite
        # In a high-concurrency DB this is bad, but for daily lambda strictly sequential it's fine.
        # Alternatively we could just append to file object? S3 doesn't support append.
        # Must rewrite full file.
        all_txns = existing + to_add
        write_transactions(all_txns)
        
    return len(to_add)

def update_transaction(transaction_id: str, classification: str, classified_by: str, percentage: int | None) -> bool:
    transactions = read_transactions()
    updated = False
    
    for txn in transactions:
        if txn["transaction_id"] == transaction_id:
            if txn["classification"]:
                return False # Already classified
                
            txn["classification"] = classification
            txn["classified_by"] = classified_by
            txn["percentage"] = str(percentage) if percentage is not None else ""
            updated = True
            break
            
    if updated:
        write_transactions(transactions)
        
    return updated

def exclude_transaction(transaction_id: str) -> bool:
    transactions = read_transactions()
    updated = False
    
    for txn in transactions:
        if txn["transaction_id"] == transaction_id:
            txn["excluded"] = "true"
            updated = True
            break
            
    if updated:
        write_transactions(transactions)
        
    return updated

def update_transaction_note(transaction_id: str, note: str) -> bool:
    transactions = read_transactions()
    updated = False
    
    for txn in transactions:
        if txn["transaction_id"] == transaction_id:
            txn["note"] = note
            updated = True
            break
            
    if updated:
        write_transactions(transactions)
        
    return updated

def reset_transaction(transaction_id: str) -> bool:
    transactions = read_transactions()
    updated = False
    
    for txn in transactions:
        if txn["transaction_id"] == transaction_id:
            txn["classification"] = ""
            txn["classified_by"] = ""
            txn["percentage"] = ""
            txn["note"] = ""
            txn["excluded"] = ""
            updated = True
            break
            
    if updated:
        write_transactions(transactions)
        
    return updated

def get_unclassified_transactions() -> list[dict]:
    txns = read_transactions()
    return [t for t in txns if not t["classification"] and not t.get("excluded")]

def get_statement_period(settlement_date: date) -> tuple[date, date]:
    """
    Calculate statement period for a settlement date (usually 1st of month).
    Period is: 10th of (month-2) to 9th of (month-1).
    Example: Settlement Feb 1st.
    Statement: Dec 10 - Jan 9.
    """
    # Go back one month to get the "statement month" (Jan)
    prev_month = settlement_date - relativedelta(months=1)
    
    # End date is 9th of that month (Jan 9)
    end_date = date(prev_month.year, prev_month.month, 9)
    
    # Start date is 10th of the month prior to that (Dec 10)
    start_month = prev_month - relativedelta(months=1)
    start_date = date(start_month.year, start_month.month, 10)
    
    return start_date, end_date

def get_transactions_for_statement_period(settlement_date: date) -> list[dict]:
    start_date, end_date = get_statement_period(settlement_date)
    all_txns = read_transactions()
    
    filtered = []
    for txn in all_txns:
        try:
            t_date = date.fromisoformat(txn["date"])
            if start_date <= t_date <= end_date:
                filtered.append(txn)
        except ValueError:
            continue
            
    return filtered

def read_users() -> dict[str, dict]:
    config = get_config()
    return {
        "user_a": {"name": config.user_a_name},
        "user_b": {"name": config.user_b_name}
    }

def get_user_by_phone(phone: str) -> dict | None:
    users = read_users()
    for uid, data in users.items():
        if data["phone"] == phone:
            return {"id": uid, **data}
    return None

def get_other_user(user_id: str) -> dict:
    users = read_users()
    if user_id == "user_a":
        return {"id": "user_b", **users["user_b"]}
    return {"id": "user_a", **users["user_a"]}

# --- Cursor Management ---
CURSOR_FILENAME = "plaid_cursor.txt"

def get_cursor() -> str | None:
    config = get_config()
    s3 = get_s3_client()
    
    try:
        response = s3.get_object(Bucket=config.s3_bucket, Key=CURSOR_FILENAME)
        content = response["Body"].read().decode("utf-8").strip()
        return content if content else None
    except Exception as e:
        if "NoSuchKey" in str(e):
            return None
        raise e

def save_cursor(cursor: str) -> None:
    if not cursor:
        return
        
    config = get_config()
    s3 = get_s3_client()
    
    s3.put_object(
        Bucket=config.s3_bucket,
        Key=CURSOR_FILENAME,
        Body=cursor.encode("utf-8"),
        ContentType="text/plain"
    )
