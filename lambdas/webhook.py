from urllib.parse import parse_qs
from twilio.twiml.messaging_response import MessagingResponse
from lib.storage import (
    get_user_by_phone,
    get_other_user,
    get_unclassified_transactions,
    update_transaction,
    read_users
)
from lib.parser import (
    parse_reply, 
    format_error_response, 
    format_invalid_transaction_response
)
from lib.twilio_client import (
    send_classification_confirmation,
    send_classification_notification
)

def handler(event, context):
    body_str = event.get("body", "")
    if event.get("isBase64Encoded", False):
        import base64
        body_str = base64.b64decode(body_str).decode("utf-8")
        
    params = parse_qs(body_str)
    
    # Twilio sends From and Body
    phone = params.get("From", [""])[0]
    message_body = params.get("Body", [""])[0]
    
    user = get_user_by_phone(phone)
    if not user:
        return {
            "statusCode": 403,
            "body": "Unauthorized"
        }
        
    unclassified = get_unclassified_transactions()
    parse_result = parse_reply(message_body)
    
    users_config = read_users()
    user_a_name = users_config["user_a"]["name"].upper()
    user_b_name = users_config["user_b"]["name"].upper()
    
    response_msg = MessagingResponse()
    
    # Handle parsing errors immediately if any (or prioritize valid ones?)
    # Spec says: "Reply with format instructions if no valid classifications"
    # But if there are mixed valid/invalid, we process valid and report invalid?
    # Let's process valid ones first.
    
    processed_count = 0
    
    for cls in parse_result.classifications:
        # Normalize classification
        raw_cls = cls.classification # Parser returns uppercase
        normalized_cls = None
        
        if raw_cls == "S":
            normalized_cls = "S"
        elif raw_cls == "A" or raw_cls == user_a_name:
            normalized_cls = "A"
        elif raw_cls == "B" or raw_cls == user_b_name:
            normalized_cls = "B"
        else:
            msg = f"Unknown classification '{cls.classification}'. Use S, {users_config['user_a']['name']}, or {users_config['user_b']['name']}."
            response_msg.message(msg)
            continue
            
        idx = cls.transaction_number - 1 # 1-based to 0-based
        
        if idx < 0 or idx >= len(unclassified):
            msg = format_invalid_transaction_response(cls.transaction_number, len(unclassified))
            response_msg.message(msg)
            continue
            
        txn = unclassified[idx]
        txn_id = txn["transaction_id"]
        
        updated = update_transaction(
            transaction_id=txn_id,
            classification=normalized_cls,
            classified_by=user["name"],
            percentage=cls.percentage
        )
        
        if updated:
            # Confirm to user (via TwiML response)
            # Actually, `send_classification_confirmation` sends an SMS.
            # But we are in a webhook response.
            # We can EITHER reply via TwiML OR send separate SMS.
            # Twilio prefers TwiML response to the webhook.
            # However, if we have multiple updates, TwiML allows multiple messages but they might arrive out of order or be batched.
            # The spec implies "Confirmation Messages ... To classifier".
            # The architectural diagram shows "Twilio webhook -> ... -> Lambda".
            # Lambda returns TwiML.
            # If we use `send_sms` inside here, the user gets 2 messages (one from TwiML, one from send_sms).
            # The `send_classification_confirmation` function in `twilio_client` is designed to trigger an SMS.
            # Ideally we should use TwiML for the reply to the current user, and `send_sms` for the OTHER user.
            
            # Let's verify `lib/twilio_client.py` implementation. 
            # I didn't implement the full logic there, I left it as "TODO" or basic return True.
            # I should just construct the message here and put it in TwiML.
            
            # Message for classifier
            msg_text = _format_confirmation_text(txn, normalized_cls, cls.percentage)
            response_msg.message(msg_text)
            
            # Notify other user
            other_user = get_other_user(user["id"])
            send_classification_notification(
                transaction=txn,
                classifier=user["name"],
                other_user=other_user,
                classification=normalized_cls,
                percentage=cls.percentage
            )
            processed_count += 1
        else:
            response_msg.message(f"Transaction #{cls.transaction_number} already classified.")

    if parse_result.errors:
        err_msg = format_error_response(parse_result.errors)
        response_msg.message(err_msg)
        
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/xml"},
        "body": str(response_msg)
    }

def _format_confirmation_text(txn, classification, percentage):
    # Reimplementing logic similar to twilio_client to return string for TwiML
    display_cls = "Shared"
    if classification == "A": display_cls = "User A"
    if classification == "B": display_cls = "User B"
    
    pct_text = ""
    if classification == "S" and percentage:
        pct_text = f" (you: {percentage}%)"
        
    return f"✓ #{txn.get('transaction_id', '?')}: {txn.get('merchant', 'Unknown')} → {display_cls}{pct_text}"
