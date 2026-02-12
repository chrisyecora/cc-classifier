import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file
load_dotenv()

from lib.discord_client import send_error_notification

def main():
    print("Sending test error notification to Discord...")
    try:
        success = send_error_notification("This is a test error message manually triggered from scripts/test_error.py")
        if success:
            print("✅ Error notification sent successfully!")
        else:
            print("❌ Failed to send error notification. Check your DISCORD_BOT_TOKEN and DISCORD_CLASSIFICATIONS_CHANNEL_ID.")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    main()
