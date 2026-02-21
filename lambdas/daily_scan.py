from datetime import date
from lib.plaid_client import fetch_new_transactions
from lib.storage import (
    append_transactions, 
    get_cursor,
    save_cursor,
    get_transaction,
    delete_transaction,
    update_transaction_details
)
from lib.discord_client import send_transaction_notification, send_settlement_notification, send_error_notification
from lib.settlement import calculate_settlement, format_settlement_message

def handler(event, context):
    """
    Handles scheduled events from EventBridge.
    Route based on resources ARN or specific detail-type if available.
    """
    resources = event.get("resources", [])
    
    # Check if monthly settlement
    is_monthly = any("MonthlySettlement" in r for r in resources)
    
    try:
        if is_monthly:
            _handle_monthly_settlement()
        else:
            # Default to daily scan
            _handle_daily_scan()
    except Exception as e:
        print(f"Error during execution: {e}")
        send_error_notification(str(e))
        raise e

def _handle_daily_scan():
    # Cursor-based sync
    cursor = get_cursor()
    
    # fetch_new_transactions handles logic and returns 3 lists + cursor
    added, modified, removed, new_cursor = fetch_new_transactions(cursor)
    
    if not added and not modified and not removed:
        print("No new/modified/removed transactions.")
        if new_cursor and new_cursor != cursor:
            save_cursor(new_cursor)
            print(f"Updated cursor: {new_cursor}")
        return

    # 1. Process Added Transactions
    transactions_to_save = []
    transactions_to_notify = []
    
    for txn in added:
        pending_id = txn.get("pending_transaction_id")
        inherited = False
        
        if pending_id:
            # Check if we have the pending transaction in DB
            pending_txn = get_transaction(pending_id)
            if pending_txn:
                print(f"Found pending transaction {pending_id} for new transaction {txn['transaction_id']}")
                # Inherit classification data
                txn['classification'] = pending_txn.get('classification', '')
                txn['classified_by'] = pending_txn.get('classified_by', '')
                txn['percentage'] = pending_txn.get('percentage', '')
                txn['note'] = pending_txn.get('note', '')
                txn['excluded'] = pending_txn.get('excluded', '')
                
                # If it was already classified or excluded, we consider it handled.
                if txn['classification'] or txn['excluded'] == 'true':
                    inherited = True
        
        transactions_to_save.append(txn)
        if not inherited:
            transactions_to_notify.append(txn)
            
    if transactions_to_save:
        count = append_transactions(transactions_to_save)
        print(f"Added {count} new transactions (saved {len(transactions_to_save)} total).")
        
    # 2. Process Modified Transactions
    for txn in modified:
        # We only update details, preserving classification
        update_transaction_details(
            txn['transaction_id'],
            txn['amount'],
            txn['date'],
            txn['merchant'],
            txn.get('name') or ''
        )
    if modified:
        print(f"Processed {len(modified)} modified transactions.")
        
    # 3. Process Removed Transactions
    for txn in removed:
        delete_transaction(txn['transaction_id'])
    if removed:
        print(f"Processed {len(removed)} removed transactions.")

    # Save cursor after processing
    if new_cursor:
        save_cursor(new_cursor)
        print(f"Saved new cursor: {new_cursor}")
    
    # Notify ONLY for truly new/unclassified transactions
    if transactions_to_notify:
        send_transaction_notification(transactions_to_notify)
    else:
        print("No new transactions to notify.")

def _handle_monthly_settlement():
    today = date.today()
    # Calculate for the statement period ending last month
    result = calculate_settlement(today)
    msg = format_settlement_message(result)
    send_settlement_notification(msg)
