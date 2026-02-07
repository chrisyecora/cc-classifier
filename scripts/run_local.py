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
        if len(sys.argv) < 4:
            print("Usage: python scripts/run_local.py webhook <phone_number> <message>")
            print("Example: python scripts/run_local.py webhook +15551234567 '1S'")
            return
            
        phone = sys.argv[2]
        body = sys.argv[3]
        
        print(f"--- Running Webhook (Local) ---")
        print(f"From: {phone}")
        print(f"Body: {body}")
        
        # Construct event matching API Gateway/Twilio
        from urllib.parse import quote
        encoded_body = f"Body={quote(body)}&From={quote(phone)}"
        
        event = {
            "body": encoded_body,
            "isBase64Encoded": False
        }
        
        try:
            response = webhook_handler(event, None)
            print("\nResponse:")
            print(response)
        except Exception as e:
            print(f"\nError running webhook: {e}")
            import traceback
            traceback.print_exc()

    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
