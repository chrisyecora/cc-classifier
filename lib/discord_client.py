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

import time

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
        
        # Handle Rate Limit
        if response.status_code == 429:
            retry_after = response.json().get('retry_after', 1)
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after + 0.1)
            # Retry once
            response = requests.post(url, headers=headers, json=payload)
            
        response.raise_for_status()
        time.sleep(0.5) # Basic throttle to be nice
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

def create_select_menu(custom_id: str, options: list, placeholder: str = "Select...") -> dict:
    """Helper to create a Select Menu component."""
    return {
        "type": 3, # String Select
        "custom_id": custom_id,
        "options": options,
        "placeholder": placeholder
    }

def create_undo_button(txn_id: str) -> dict:
    """Helper to create an Undo button (Red)."""
    return create_button("Undo", f"undo:{txn_id}", 4)

def build_classification_components(txn_id: str) -> list:
    """Builds the buttons and select menu for classifying a transaction."""
    config = get_config()
    user_a = config.user_a_name
    user_b = config.user_b_name
    
    # Row 1: Quick Buttons
    buttons = [
        create_button("Shared (50/50)", f"classify:{txn_id}:S", 3), # Green
        create_button(f"{user_a}", f"classify:{txn_id}:A", 2),
        create_button(f"{user_b}", f"classify:{txn_id}:B", 2),
        create_button("Custom $", f"classify_custom_amount:{txn_id}", 2) # Grey
    ]
    
    # Row 2: Custom Split Dropdown
    select_options = []
    for pct in [60, 65, 70, 75]:
        select_options.append({
            "label": f"You pay {pct}%",
            "value": f"S{pct}",
            "description": f"Split: {pct}/{100-pct}"
        })
        
    select_menu = create_select_menu(
        custom_id=f"classify_split:{txn_id}", 
        options=select_options,
        placeholder="Custom Split (You pay %)..."
    )
    
    return [
        create_action_row(buttons),
        create_action_row([select_menu])
    ]

def send_transaction_notification(transactions: list[dict]) -> bool:
    """
    Sends a notification with interactive buttons and dropdown for each unclassified transaction.
    """
    success = True
    config = get_config()
    
    for txn in transactions:
        txn_id = txn["transaction_id"]
        merchant = txn["merchant"]
        amount = txn["amount"]
        date = txn["date"]
        
        content = f"**New Transaction**\nMerchant: {merchant}\nAmount: ${amount}\nDate: {date}"
        components = build_classification_components(txn_id)
        
        if not send_message(content, config.discord_classifications_channel_id, components):
            success = False
            
    return success

def send_settlement_notification(message: str) -> bool:
    config = get_config()
    return send_message(message, config.discord_settlements_channel_id)

