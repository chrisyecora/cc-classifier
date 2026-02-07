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
        
    # 3 = MESSAGE_COMPONENT (Button click)
    if t == 3:
        return handle_button_click(interaction)
        
    return {"statusCode": 400, "body": "Unknown interaction type"}

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
    
    # Update DB
    # We pass the Discord username as 'classified_by'. 
    # Ideally we map this to configured names, but for simplicity we use the Discord name 
    # or just rely on the button choice (since buttons are labeled with names).
    # Actually, storage expects "Chris" or "Caro". 
    # Let's use the button value 'A' or 'B' to lookup the configured name if we want consistency,
    # OR just pass the user who clicked it.
    
    # Let's map A/B back to names for the confirmation message
    config_users = read_users()
    display_cls = "Shared"
    if classification == "A":
        display_cls = config_users["user_a"]["name"]
    elif classification == "B":
        display_cls = config_users["user_b"]["name"]
        
    updated = update_transaction(txn_id, classification, user, None)
    
    if updated:
        return json_response(7, f"✅ Classified as **{display_cls}** by {user}.", components=[])
    else:
        return json_response(7, f"⚠️ Transaction already classified.", components=[])

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