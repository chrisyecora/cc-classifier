import json
from lib.discord_client import verify_discord_signature, create_button, create_action_row, build_classification_components
from lib.storage import update_transaction, read_users, reset_transaction, read_transactions

def handler(event, context):
    headers = event.get("headers", {})
    signature = headers.get("x-signature-ed25519") or headers.get("X-Signature-Ed25519")
    timestamp = headers.get("x-signature-timestamp") or headers.get("X-Signature-Timestamp")
    body = event.get("body", "")
    
    if not signature or not timestamp:
        return {"statusCode": 401, "body": "Missing signature headers"}
        
    if not verify_discord_signature(signature, timestamp, body):
        return {"statusCode": 401, "body": "Invalid signature"}
        
    interaction = json.loads(body)
    t = interaction.get("type")
    
    if t == 1: # PING
        return {"statusCode": 200, "body": json.dumps({"type": 1})}
        
    if t == 3: # MESSAGE_COMPONENT
        data = interaction.get("data", {})
        component_type = data.get("component_type")
        if component_type == 2:
            return handle_button_click(interaction)
        elif component_type == 3:
            return handle_select_menu(interaction)
            
    if t == 5: # MODAL_SUBMIT
        return handle_modal_submit(interaction)
            
    return {"statusCode": 400, "body": "Unknown interaction type"}

def handle_select_menu(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    values = data.get("values", [])
    if not values: return json_response(4, "No value selected.")
    
    value = values[0]
    classification = value[0]
    try:
        percentage = float(value[1:])
    except ValueError:
        percentage = None
        
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    parts = custom_id.split(":")
    txn_id = parts[1]
    
    return _process_update(interaction, txn_id, classification, user, percentage)

def handle_modal_submit(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    parts = custom_id.split(":")
    txn_id = parts[1]
    
    try:
        input_value = data["components"][0]["components"][0]["value"]
        user_amount = float(input_value)
    except (KeyError, ValueError):
        return json_response(4, "Invalid amount format.")
        
    all_txns = read_transactions()
    txn = next((t for t in all_txns if t["transaction_id"] == txn_id), None)
    if not txn: return json_response(4, "Transaction not found.")
        
    total_amount = float(txn["amount"])
    
    valid = True
    if total_amount < 0:
        if user_amount < total_amount or user_amount > 0: valid = False
    else:
        if user_amount < 0 or user_amount > total_amount: valid = False

    if not valid:
        return json_response(4, f"Amount must be between 0 and {total_amount}")
        
    percentage = round((user_amount / total_amount) * 100, 2) if total_amount != 0 else 0
    return _process_update(interaction, txn_id, "S", user, percentage)

def handle_button_click(interaction):
    data = interaction.get("data", {})
    custom_id = data.get("custom_id", "")
    user = interaction.get("member", {}).get("user", {}).get("username", "Unknown")
    
    parts = custom_id.split(":")
    action = parts[0]
    
    if action == "undo":
        return handle_undo(interaction, parts[1])
    
    if action == "classify_custom_amount":
        txn_id = parts[1]
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "type": 9,
                "data": {
                    "custom_id": f"modal_custom_amount:{txn_id}",
                    "title": "Enter Split Amount",
                    "components": [{
                        "type": 1,
                        "components": [{
                            "type": 4,
                            "custom_id": "amount_input",
                            "label": "Amount you pay ($)",
                            "style": 1,
                            "placeholder": "e.g. 25.50",
                            "required": True
                        }]
                    }]
                }
            })
        }
        
    if len(parts) != 3 or action != "classify":
        return json_response(4, "Invalid button action.")
        
    return _process_update(interaction, parts[1], parts[2], user, None)

def handle_undo(interaction, txn_id):
    if reset_transaction(txn_id):
        all_txns = read_transactions()
        txn = next((t for t in all_txns if t["transaction_id"] == txn_id), None)
        if txn:
            content = f"**New Transaction**\nMerchant: {txn['merchant']}\nAmount: ${txn['amount']}\nDate: {txn['date']}"
            components = build_classification_components(txn_id)
            return json_response(7, content, components)
    return json_response(4, "Error: Could not undo classification.")

def _process_update(interaction, txn_id, classification, user, percentage):
    config_users = read_users()
    display_cls = "Shared"
    
    if classification == "A":
        display_cls = config_users["user_a"]["name"]
    elif classification == "B":
        display_cls = config_users["user_b"]["name"]
    elif classification == "S":
        if percentage is not None:
            display_cls = f"Shared ({percentage}%)"
        else:
            display_cls = "Shared (50/50)"
        
    updated = update_transaction(txn_id, classification, user, percentage)
    
    message_obj = interaction.get("message")
    original_content = message_obj.get("content", "") if message_obj else ""
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
        # Include Undo button
        undo_btn = create_button("Undo", f"undo:{txn_id}", 4) # Red
        components = [create_action_row([undo_btn])]
        return json_response(7, f"{summary_text} ✅ Classified as **{display_cls}** by {user}", components=components)
    else:
        return json_response(7, f"{summary_text} ⚠️ Already classified", components=[])

def json_response(type_code, content, components=None):
    data = {"content": content}
    if components is not None: data["components"] = components
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"type": type_code, "data": data})
    }
