from datetime import date, timedelta
from lib.plaid_client import fetch_transactions
from lib.storage import (
    append_transactions, 
    get_unclassified_transactions
)
from lib.discord_client import send_transaction_notification, send_settlement_notification
from lib.settlement import calculate_settlement, format_settlement_sms

def handler(event, context):
    """
    Handles scheduled events from EventBridge.
    Route based on resources ARN or specific detail-type if available.
    """
    resources = event.get("resources", [])
    
    # Check if monthly settlement
    is_monthly = any("MonthlySettlement" in r for r in resources)
    if is_monthly:
        _handle_monthly_settlement()
    else:
        # Default to daily scan
        _handle_daily_scan()

def _handle_daily_scan():
    today = date.today()
    # Fetch previous day (or last 2 days to be safe)
    start_date = today - timedelta(days=2)
    
    transactions = fetch_transactions(start_date, today)
    if not transactions:
        print("No transactions fetched.")
        return
        
    added = append_transactions(transactions)
    print(f"Added {added} new transactions.")
    
    unclassified = get_unclassified_transactions()
    if unclassified:
        # Discord client handles sending to the configured channel
        send_transaction_notification(unclassified)
    else:
        print("No unclassified transactions pending.")

def _handle_monthly_settlement():
    today = date.today()
    # Calculate for the statement period ending last month (usually)
    # The logic in settlement.py handles period calculation based on settlement date.
    
    result = calculate_settlement(today)
    
    # Using format_settlement_sms but for Discord message
    msg = format_settlement_sms(result)
    
    send_settlement_notification(msg)