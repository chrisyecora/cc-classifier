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
        print("  python scripts/run_local.py settle [override_date]")
        print("  python scripts/run_local.py webhook <custom_id>")
        print("  python scripts/run_local.py update <json_string_or_file_path>")
        print("  python scripts/run_local.py resend <transaction_id>")
        print("  python scripts/run_local.py reset")
        print("  python scripts/run_local.py dump")
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
            "data": {
                "custom_id": custom_id,
                "component_type": 2 # Button
            },
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

    elif command == "update":
        if len(sys.argv) < 3:
            print("Usage: python scripts/run_local.py update <json_string_or_file_path>")
            return

        input_data = sys.argv[2]
        import json
        from decimal import Decimal

        # Try to read as file first
        if os.path.isfile(input_data):
            try:
                with open(input_data, 'r') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading file: {e}")
                return
        else:
            content = input_data

        try:
            item_data = json.loads(content, parse_float=Decimal)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return

        from lib.storage import get_table, PK_TRX
        
        if 'transaction_id' not in item_data:
            print("Error: JSON must contain 'transaction_id'")
            return

        # Prepare item for DynamoDB
        item = item_data.copy()
        item['pk'] = PK_TRX
        item['sk'] = item_data['transaction_id']
        
        print(f"Updating transaction {item['sk']}...")
        
        try:
            table = get_table()
            table.put_item(Item=item)
            print("Update complete.")
        except Exception as e:
            print(f"Error updating item: {e}")

    elif command == "resend":
        if len(sys.argv) < 3:
            print("Usage: python scripts/run_local.py resend <transaction_id>")
            return

        txn_id = sys.argv[2]
        from lib.storage import get_transaction, read_users
        from lib.discord_client import send_message, build_classification_embed, build_classification_components, build_post_classification_components
        from config import get_config

        print(f"Fetching transaction {txn_id}...")
        txn = get_transaction(txn_id)
        if not txn:
            print(f"Error: Transaction {txn_id} not found in database.")
            return

        config = get_config()
        config_users = read_users()
        
        # Decide which components to show
        if txn.get('classification') or txn.get('excluded') == "true":
            components = build_post_classification_components(txn_id)
        else:
            components = build_classification_components(txn_id)

        embed = build_classification_embed(txn, config_users)
        
        print(f"Sending message to channel {config.discord_classifications_channel_id}...")
        if send_message("", config.discord_classifications_channel_id, components=components, embeds=[embed]):
            print("Success: Interactive message resent to Discord.")
        else:
            print("Error: Failed to send message to Discord.")

    elif command == "reset":
        print("--- Resetting DynamoDB Table (Deleting All Data) ---")
        confirm = input("Are you sure you want to delete ALL data? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            return

        from lib.storage import get_table, PK_TRX, PK_CONFIG
        import boto3
        
        table = get_table()
        
        # Scan and delete
        # Note: This is inefficient for large tables but fine for dev/testing.
        scan = table.scan()
        with table.batch_writer() as batch:
            for each in scan['Items']:
                batch.delete_item(
                    Key={
                        'pk': each['pk'],
                        'sk': each['sk']
                    }
                )
        print("Table cleared.")

    elif command == "dump":
        print("--- Dumping DynamoDB Table ---")
        from lib.storage import get_table
        import json
        from decimal import Decimal

        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return str(o)
                return super(DecimalEncoder, self).default(o)

        table = get_table()
        try:
            response = table.scan()
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            print(json.dumps(items, cls=DecimalEncoder, indent=2))
            print(f"\nTotal items: {len(items)}")
        except Exception as e:
            print(f"Error dumping table: {e}")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python scripts/run_local.py delete <transaction_id>")
            return
            
        txn_id = sys.argv[2]
        from lib.storage import delete_transaction, get_transaction
        
        txn = get_transaction(txn_id)
        if txn:
            print(f"Found transaction: {txn}")
        else:
            print(f"Warning: Transaction {txn_id} not found.")

        confirm = input(f"Are you sure you want to delete transaction {txn_id}? (y/n): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

        if delete_transaction(txn_id):
            print(f"Successfully deleted transaction {txn_id}.")
        else:
            print(f"Failed to delete transaction {txn_id}.")

    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
