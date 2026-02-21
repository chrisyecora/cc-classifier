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

def send_message(content: str, channel_id: str, components: list = None, embeds: list = None) -> bool:
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
    if embeds:
        payload["embeds"] = embeds
        
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
        create_button("Custom $", f"classify_custom_amount:{txn_id}", 2), # Grey
        create_button("Ignore", f"exclude:{txn_id}", 2) # Grey
    ]
    
    # Row 2: Custom Split Dropdown
    select_options = []
    for pct in [25, 30, 35, 40, 60, 65, 70, 75]:
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

def build_post_classification_components(txn_id: str) -> list:
    """Builds the buttons displayed after a transaction is classified."""
    return [create_action_row([
        create_button("Undo", f"undo:{txn_id}", 4), # Red
        create_button("Add Note", f"note:{txn_id}", 2) # Secondary (Grey)
    ])]

def build_note_modal(txn_id: str, current_note: str = "") -> dict:
    """Builds the modal for adding/editing a note."""
    return {
        "title": "Add/Edit Note",
        "custom_id": f"modal_note:{txn_id}",
        "components": [create_action_row([{
            "type": 4, # Text Input
            "custom_id": "note_input",
            "label": "Note",
            "style": 2, # Paragraph
            "value": current_note,
            "required": False,
            "max_length": 200
        }])]
    }

def build_classification_embed(txn: dict, config_users: dict) -> dict:
    """Builds the rich embed showing a transaction's classification status."""
    classification = txn.get("classification", "")
    classified_by = txn.get("classified_by", "")
    percentage_str = txn.get("percentage", "")
    note = txn.get("note", "")
    excluded = txn.get("excluded") == "true"
    
    display_cls = "Shared"
    if classification == "A":
        display_cls = config_users["user_a"]["name"]
    elif classification == "B":
        display_cls = config_users["user_b"]["name"]
    elif classification == "S":
        if percentage_str:
            display_cls = f"Shared ({percentage_str}%)"
        else:
            display_cls = "Shared (50/50)"

    embed = {
        "title": txn.get('merchant', 'Unknown Merchant'),
        "description": f"**${txn.get('amount', '0.00')}** on {txn.get('date', 'Unknown Date')}",
        "color": 0x57F287, # Green
        "fields": []
    }
    
    if excluded:
        embed["color"] = 0x95A5A6 # Grey
        embed["fields"].append({"name": "Status", "value": "**Ignored**", "inline": True})
    elif classification:
        embed["fields"].append({"name": "Classified As", "value": f"**{display_cls}**", "inline": True})
        embed["fields"].append({"name": "By", "value": classified_by, "inline": True})
    else:
        embed["color"] = 0x3498DB # Blue (Unclassified)
        embed["fields"].append({"name": "Status", "value": "**Pending Classification**", "inline": True})
    
    if note:
        embed["fields"].append({"name": "Note", "value": note, "inline": False})
        
    return embed

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

def send_error_notification(error_message: str) -> bool:
    """Sends an error notification to the Discord channel."""
    config = get_config()
    
    # 0xE74C3C is Red
    embed = {
        "title": "🚨 System Error",
        "description": f"```{error_message}```",
        "color": 0xE74C3C 
    }
    
    # Send to classifications channel as it's the main "admin" view usually
    return send_message("", config.discord_classifications_channel_id, embeds=[embed])

