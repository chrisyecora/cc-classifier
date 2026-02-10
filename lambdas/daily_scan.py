from datetime import date
from lib.plaid_client import fetch_new_transactions
from lib.storage import (
    append_transactions, 
    get_cursor,
    save_cursor
)
from lib.discord_client import send_transaction_notification, send_settlement_notification
from lib.settlement import calculate_settlement, format_settlement_message

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
    # Cursor-based sync
    cursor = get_cursor()
    
    # fetch_new_transactions handles the logic of "if cursor is None, fetch all but keep recent"
    transactions, new_cursor = fetch_new_transactions(cursor)
    
    if not transactions:
        print("No new transactions fetched.")
        # Even if no transactions, we must save the new cursor to advance state!
        # (Unless API failed, but here we assume success)
        if new_cursor and new_cursor != cursor:
            save_cursor(new_cursor)
            print(f"Updated cursor: {new_cursor}")
        return
        
    added = append_transactions(transactions)
    print(f"Added {added} new transactions.")
    
    # Save cursor after successful append
    if new_cursor:
        save_cursor(new_cursor)
        print(f"Saved new cursor: {new_cursor}")
    
    # Notify ONLY for newly fetched transactions (Fire-and-Forget)
    if transactions:
        send_transaction_notification(transactions)
    else:
        print("No new transactions to notify.")

def _handle_monthly_settlement():
    today = date.today()
    # Calculate for the statement period ending last month
    result = calculate_settlement(today)
    msg = format_settlement_message(result)
    send_settlement_notification(msg)
