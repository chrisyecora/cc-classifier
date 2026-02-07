import json
import requests
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from config import get_config

def verify_discord_signature(signature: str, timestamp: str, body: str) -> bool:
    """Verifies the Ed25519 signature of a Discord interaction."""
    config = get_config()
    public_key = config.discord_public_key
    
    if not public_key:
        return False
        
    verify_key = VerifyKey(bytes.fromhex(public_key))
    
    try:
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except BadSignatureError:
        return False

def send_message(content: str, channel_id: str, components: list = None) -> bool:
    """Sends a message to the specified Discord channel."""
    config = get_config()
    token = config.discord_bot_token
    
    if not token or not channel_id:
        return False
        
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    payload = {"content": content}
    if components:
        payload["components"] = components
        
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Discord message: {e}")
        return False

def create_action_row(buttons: list) -> dict:
    """Helper to create an Action Row component."""
    return {
        "type": 1,
        "components": buttons
    }

def create_button(label: str, custom_id: str, style: int = 1) -> dict:
    """
    Helper to create a button component.
    Styles: 1=Primary(Blurple), 2=Secondary(Grey), 3=Success(Green), 4=Danger(Red)
    """
    return {
        "type": 2,
        "label": label,
        "style": style,
        "custom_id": custom_id
    }

def send_transaction_notification(transactions: list[dict]) -> bool:
    """
    Sends a notification with interactive buttons for each unclassified transaction.
    Since Discord has a limit on message size and components, we'll send one message per transaction
    to keep it clean and allow specific "Reply" buttons for that transaction.
    """
    success = True
    config = get_config()
    
    user_a = config.user_a_name
    user_b = config.user_b_name
    
    for txn in transactions:
        txn_id = txn["transaction_id"]
        merchant = txn["merchant"]
        amount = txn["amount"]
        date = txn["date"]
        
        content = f"**New Transaction**\nMerchant: {merchant}\nAmount: ${amount}\nDate: {date}"
        
        # Create buttons for this specific transaction
        # Custom ID format: "action:txn_id:value"
        # e.g., "classify:plaid_123:S"
        buttons = [
            create_button("Shared (50/50)", f"classify:{txn_id}:S", 1),
            create_button(f"{user_a}", f"classify:{txn_id}:A", 2),
            create_button(f"{user_b}", f"classify:{txn_id}:B", 2)
        ]
        
        # We can add more complex split options later if needed, but 3 buttons is a good start.
        components = [create_action_row(buttons)]
        
        if not send_message(content, config.discord_classifications_channel_id, components):
            success = False
            
    return success

def send_settlement_notification(message: str) -> bool:
    config = get_config()
    return send_message(message, config.discord_settlements_channel_id)

