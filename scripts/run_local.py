import sys
import os
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file
load_dotenv()

from lambdas.daily_scan import handler as daily_handler
from lambdas.webhook import handler as webhook_handler

# Configure logging
logging.basicConfig(level=logging.INFO)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/run_local.py scan")
        print("  python scripts/run_local.py webhook <phone_number> <message>")
        return

    command = sys.argv[1]
    
    if command == "scan":
        print("--- Running Daily Scan (Local) ---")
        # Simulate daily event
        event = {"resources": ["arn:aws:events:rule/DailySchedule"]}
        try:
            daily_handler(event, None)
            print("\nScan complete.")
        except Exception as e:
            print(f"\nError running scan: {e}")
            import traceback
            traceback.print_exc()
        
    elif command == "settle":
        print("--- Running Settlement (Local) ---")
        os.environ["IS_DRY_RUN"] = "true"
        
        # Simulate monthly event
        event = {"resources": ["arn:aws:events:rule/MonthlySettlement"]}
        
        # Allow overriding date for testing
        # Usage: python scripts/run_local.py settle 2026-03-01
        if len(sys.argv) > 2:
            override_date = sys.argv[2]
            print(f"Overriding date to: {override_date}")
            
            # Monkeypatch date.today()
            import datetime
            class MockDate(datetime.date):
                @classmethod
                def today(cls):
                    return cls.fromisoformat(override_date)
            
            # Patch in the modules that use date.today()
            import lambdas.daily_scan
            lambdas.daily_scan.date = MockDate
            
        try:
            daily_handler(event, None)
            print("\nSettlement run complete.")
        except Exception as e:
            print(f"\nError running settlement: {e}")
            import traceback
            traceback.print_exc()

    elif command == "backfill":
        # Usage: python scripts/run_local.py backfill 2026-01-10 2026-02-07
        if len(sys.argv) < 4:
            print("Usage: python scripts/run_local.py backfill <start_date> <end_date>")
            print("Example: python scripts/run_local.py backfill 2026-01-10 2026-02-07")
            return
            
        start_str = sys.argv[2]
        end_str = sys.argv[3]
        
        print(f"--- Running Backfill: {start_str} to {end_str} ---")
        
        from datetime import date
        from lib.plaid_client import fetch_transactions
        from lib.storage import append_transactions, get_unclassified_transactions
        from lib.discord_client import send_transaction_notification
        
        try:
            start_date = date.fromisoformat(start_str)
            end_date = date.fromisoformat(end_str)
            
            print("Fetching transactions from Plaid...")
            transactions = fetch_transactions(start_date, end_date)
            
            if not transactions:
                print("No transactions found in this range.")
            else:
                print(f"Found {len(transactions)} transactions. Saving to S3...")
                added = append_transactions(transactions)
                print(f"Added {added} new transactions to storage.")
                
                # Optional: Send notifications for these backfilled items?
                # Usually backfills might be large, so maybe ask user or just do it.
                # Let's do it to ensure they get classified.
                if added > 0:
                    print("Sending Discord notifications...")
                    unclassified = get_unclassified_transactions()
                    # Filter only the ones we just added? 
                    # append_transactions doesn't return IDs. 
                    # But get_unclassified_transactions returns ALL unclassified.
                    # This is safe, ensures nothing is missed.
                    send_transaction_notification(unclassified)
                    print("Notifications sent.")
                    
        except Exception as e:
            print(f"\nError running backfill: {e}")
            import traceback
            traceback.print_exc()

    elif command == "plaid-test":
        print("--- Testing Plaid Connection Directly ---")
        from lib.plaid_client import fetch_transactions
        from datetime import date, timedelta
        
        today = date.today()
        start = today - timedelta(days=30) # Last 30 days
        
        print(f"Fetching transactions from {start} to {today}...")
        try:
            txns = fetch_transactions(start, today)
            print(f"\nSuccess! Found {len(txns)} transactions:")
            for t in txns:
                print(f"- {t['date']}: {t['merchant']} (${t['amount']})")
        except Exception as e:
            print(f"\nError fetching from Plaid: {e}")
            import traceback
            traceback.print_exc()

    elif command == "webhook":
        if len(sys.argv) < 3:
            print("Usage: python scripts/run_local.py webhook <custom_id>")
            print("Example: python scripts/run_local.py webhook 'classify:tx123:S'")
            return
            
        custom_id = sys.argv[2]
        
        print(f"--- Running Webhook (Local Discord Interaction) ---")
        print(f"Custom ID: {custom_id}")
        
        import json
        # Construct Discord Interaction JSON
        body_json = {
            "type": 3, # MESSAGE_COMPONENT
            "data": {"custom_id": custom_id},
            "member": {"user": {"username": "LocalTester"}}
        }
        
        event = {
            "headers": {
                "x-signature-ed25519": "mock_sig",
                "x-signature-timestamp": "mock_ts"
            },
            "body": json.dumps(body_json),
            "isBase64Encoded": False
        }
        
        # Mock signature verification for local run
        import lambdas.webhook
        original_verify = lambdas.webhook.verify_discord_signature
        lambdas.webhook.verify_discord_signature = lambda s, t, b: True
        
        try:
            response = webhook_handler(event, None)
            print("\nResponse:")
            print(json.dumps(response, indent=2))
        except Exception as e:
            print(f"\nError running webhook: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Restore verification
            lambdas.webhook.verify_discord_signature = original_verify

    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
