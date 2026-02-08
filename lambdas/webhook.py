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
            
    # 5 = MODAL_SUBMIT
    if t == 5:
        return handle_modal_submit(interaction)
            
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

def handle_modal_submit(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    # Custom ID: modal_custom_amount:txn_id
    parts = custom_id.split(":")
    if len(parts) != 2 or parts[0] != "modal_custom_amount":
        return json_response(4, "Invalid modal submission.")
        
    txn_id = parts[1]
    
    # Get input value
    # Components structure: data -> components -> [ActionRow] -> components -> [TextInput]
    try:
        input_value = data["components"][0]["components"][0]["value"]
        user_amount = float(input_value)
    except (KeyError, ValueError):
        return json_response(4, "Invalid amount format.")
        
    # We need total amount to calculate percentage.
    # Extract from original message? Modal submit event usually contains 'message' object if triggered from message component?
    # Actually, Type 5 (Modal Submit) interaction might NOT contain the original message object if triggered from a button.
    # However, Discord documentation says: "message: The message this interaction is attached to (optional)."
    # If it's missing, we can't calculate %.
    # BUT: We have the transaction ID. We could read from DB (S3).
    # Since we are serverless and stateless, reading S3 is safer.
    
    from lib.storage import read_transactions
    all_txns = read_transactions()
    txn = next((t for t in all_txns if t["transaction_id"] == txn_id), None)
    
    if not txn:
        return json_response(4, "Transaction not found.")
        
    total_amount = float(txn["amount"])
    
    valid = True
    # For Credits (negative total), user amount must be between total and 0 (e.g. -50 <= -20 <= 0)
    if total_amount < 0:
        if user_amount < total_amount or user_amount > 0:
            valid = False
            
    # For Expenses (positive total), user amount must be between 0 and total (e.g. 0 <= 20 <= 50)
    else:
        if user_amount < 0 or user_amount > total_amount:
            valid = False

    if not valid:
        return json_response(4, f"Amount must be between 0 and {total_amount}")
        
    # Calculate percentage
    if total_amount == 0:
        percentage = 0
    else:
        percentage = round((user_amount / total_amount) * 100, 2)
        
    # Use standard update
    return _process_update(interaction, txn_id, "S", user, percentage)

def handle_button_click(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    parts = custom_id.split(":")
    action = parts[0]
    
    if action == "classify_custom_amount":
        # Return Modal
        txn_id = parts[1]
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "type": 9, # MODAL
                "data": {
                    "custom_id": f"modal_custom_amount:{txn_id}",
                    "title": "Enter Split Amount",
                    "components": [{
                        "type": 1,
                        "components": [{
                            "type": 4, # Text Input
                            "custom_id": "amount_input",
                            "label": "Amount you pay ($)",
                            "style": 1, # Short
                            "placeholder": "e.g. 25.50",
                            "required": True
                        }]
                    }]
                }
            })
        }
        
    # Format: classify:txn_id:classification
    if len(parts) != 3 or action != "classify":
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
    
    # Calculate percentage might return float, format it nicely
    if isinstance(percentage, float):
        # If integer-like, show as int
        if percentage.is_integer():
            percentage = int(percentage)
            display_cls = f"Shared ({percentage}/{100-percentage})"
        else:
            display_cls = f"Shared ({percentage:.2f}%)"
        
    updated = update_transaction(txn_id, classification, user, percentage)
    
    # Extract original message content
    # For Buttons (Type 3): interaction['message'] exists.
    # For Modals (Type 5): interaction['message'] might exist if triggered from message component.
    message_obj = interaction.get("message")
    original_content = message_obj.get("content", "") if message_obj else ""
    
    # If missing (sometimes Modals don't pass it fully or structure differs), try to reconstruct or fetch?
    # For now, we rely on it being present.
    
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