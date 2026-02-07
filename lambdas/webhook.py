import json
from lib.discord_client import verify_discord_signature
from lib.storage import update_transaction, read_users

def handler(event, context):
    headers = event.get("headers", {})
    # API Gateway might lowercase headers or not
    signature = headers.get("x-signature-ed25519") or headers.get("X-Signature-Ed25519")
    timestamp = headers.get("x-signature-timestamp") or headers.get("X-Signature-Timestamp")
    body = event.get("body", "")
    
    if not signature or not timestamp:
        return {"statusCode": 401, "body": "Missing signature headers"}
        
    if not verify_discord_signature(signature, timestamp, body):
        return {"statusCode": 401, "body": "Invalid signature"}
        
    interaction = json.loads(body)
    t = interaction.get("type")
    
    # 1 = PING
    if t == 1:
        return {
            "statusCode": 200,
            "body": json.dumps({"type": 1})
        }
        
    # 3 = MESSAGE_COMPONENT (Button click or Select Menu)
    if t == 3:
        data = interaction.get("data", {})
        component_type = data.get("component_type")
        
        # 2 = Button, 3 = Select Menu
        if component_type == 2:
            return handle_button_click(interaction)
        elif component_type == 3:
            return handle_select_menu(interaction)
            
    return {"statusCode": 400, "body": "Unknown interaction type"}

def handle_select_menu(interaction):
    data = interaction.get("data", {})
    # Custom ID: classify_split:txn_id
    custom_id = data.get("custom_id", "")
    # Values: ["S70"]
    values = data.get("values", [])
    
    if not values:
        return json_response(4, "No value selected.")
        
    value = values[0] # e.g. "S70"
    
    # Extract classification and percentage
    # S70 -> cls=S, pct=70
    classification = value[0]
    try:
        percentage = int(value[1:])
    except ValueError:
        percentage = None
        
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    parts = custom_id.split(":")
    if len(parts) != 2 or parts[0] != "classify_split":
        return json_response(4, "Invalid selection.")
        
    txn_id = parts[1]
    
    return _process_update(interaction, txn_id, classification, user, percentage)

def handle_button_click(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    # Format: classify:txn_id:classification
    parts = custom_id.split(":")
    if len(parts) != 3 or parts[0] != "classify":
        return json_response(4, "Invalid button action.")
        
    txn_id = parts[1]
    classification = parts[2]
    
    return _process_update(interaction, txn_id, classification, user, None)

def _process_update(interaction, txn_id, classification, user, percentage):
    # Update DB
    config_users = read_users()
    display_cls = "Shared"
    
    if classification == "A":
        display_cls = config_users["user_a"]["name"]
    elif classification == "B":
        display_cls = config_users["user_b"]["name"]
    elif classification == "S" and percentage:
        display_cls = f"Shared ({percentage}/{100-percentage})"
        
    updated = update_transaction(txn_id, classification, user, percentage)
    
    # Extract original message content to parse Merchant/Amount
    # Original format: "**New Transaction**\nMerchant: {merchant}\nAmount: ${amount}\nDate: {date}"
    original_content = interaction.get("message", {}).get("content", "")
    
    # Simple parse attempt (fallback to generic if parse fails)
    summary_text = f"Transaction {txn_id}"
    try:
        lines = original_content.split('\n')
        merchant = next((l.split(": ")[1] for l in lines if l.startswith("Merchant:")), "Unknown")
        amount = next((l.split(": ")[1] for l in lines if l.startswith("Amount:")), "?")
        date = next((l.split(": ")[1] for l in lines if l.startswith("Date:")), "")
        summary_text = f"{merchant} {amount} ({date})"
    except Exception:
        pass

    if updated:
        return json_response(7, f"{summary_text} ✅ Classified as **{display_cls}** by {user}", components=[])
    else:
        return json_response(7, f"{summary_text} ⚠️ Already classified", components=[])

def json_response(type_code, content, components=None):
    data = {"content": content}
    if components is not None:
        data["components"] = components
        
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "type": type_code,
            "data": data
        })
    }