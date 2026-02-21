import pytest
from lib.discord_client import (
    verify_discord_signature,
    send_message,
    create_action_row,
    create_button,
    create_select_menu,
    create_undo_button,
    build_classification_components,
    build_post_classification_components,
    build_note_modal,
    build_classification_embed,
    send_transaction_notification,
    send_settlement_notification,
    send_error_notification
)
from config import get_config

def test_verify_discord_signature_valid(mocker, env_setup):
    mocker.patch("lib.discord_client.VerifyKey")
    result = verify_discord_signature("00"*64, "ts", "body")
    assert result is True

def test_verify_discord_signature_invalid(mocker, env_setup):
    from nacl.exceptions import BadSignatureError
    mock_verify = mocker.MagicMock()
    mock_verify.verify.side_effect = BadSignatureError("Invalid")
    mocker.patch("lib.discord_client.VerifyKey", return_value=mock_verify)
    result = verify_discord_signature("00"*64, "ts", "body")
    assert result is False

def test_verify_discord_signature_no_public_key(mocker, env_setup):
    mock_config = mocker.patch("lib.discord_client.get_config")
    mock_config.return_value.discord_public_key = None
    result = verify_discord_signature("00"*64, "ts", "body")
    assert result is False

def test_send_message_success(mocker, env_setup):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200
    
    test_channel = "999"
    success = send_message("Hello", channel_id=test_channel)
    assert success is True
    
    config = get_config()
    expected_url = f"https://discord.com/api/v10/channels/{test_channel}/messages"
    mock_post.assert_called_with(
        expected_url,
        headers={"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"},
        json={"content": "Hello"}
    )

def test_send_message_failure(mocker, env_setup):
    mock_post = mocker.patch("requests.post")
    mock_post.side_effect = Exception("Error")
    
    success = send_message("Hello", channel_id="123")
    assert success is False

def test_send_message_no_token(mocker, env_setup):
    mock_config = mocker.patch("lib.discord_client.get_config")
    mock_config.return_value.discord_bot_token = None
    assert send_message("Hello", channel_id="123") is False

def test_send_message_rate_limit(mocker, env_setup):
    mock_post = mocker.patch("requests.post")
    mock_response = mocker.MagicMock()
    mock_response.status_code = 429
    mock_response.json.return_value = {"retry_after": 0.1}
    
    mock_response_success = mocker.MagicMock()
    mock_response_success.status_code = 200
    
    mock_post.side_effect = [mock_response, mock_response_success]
    mocker.patch("time.sleep")
    
    assert send_message("Hello", channel_id="123") is True
    assert mock_post.call_count == 2

def test_create_helpers():
    assert create_action_row([]) == {"type": 1, "components": []}
    assert create_button("L", "id", 1) == {"type": 2, "label": "L", "style": 1, "custom_id": "id"}
    assert create_select_menu("id", []) == {"type": 3, "custom_id": "id", "options": [], "placeholder": "Select..."}
    assert create_undo_button("txn") == {"type": 2, "label": "Undo", "style": 4, "custom_id": "undo:txn"}

def test_build_classification_components(env_setup):
    components = build_classification_components("txn1")
    assert len(components) == 2
    assert components[0]["type"] == 1
    assert components[1]["type"] == 1
    assert len(components[0]["components"]) == 5
    assert len(components[1]["components"]) == 1

def test_build_post_classification_components():
    components = build_post_classification_components("txn1")
    assert len(components) == 1
    assert len(components[0]["components"]) == 2

def test_build_note_modal():
    modal = build_note_modal("txn1", "old note")
    assert modal["title"] == "Add/Edit Note"
    assert modal["components"][0]["components"][0]["value"] == "old note"

def test_build_classification_embed():
    config_users = {"user_a": {"name": "Alice"}, "user_b": {"name": "Bob"}}
    
    # Excluded
    txn = {"merchant": "M", "amount": "10", "date": "2023", "excluded": "true"}
    embed = build_classification_embed(txn, config_users)
    assert embed["color"] == 0x95A5A6
    assert embed["fields"][0]["value"] == "**Ignored**"
    
    # Unclassified
    txn = {"merchant": "M", "amount": "10"}
    embed = build_classification_embed(txn, config_users)
    assert embed["color"] == 0x3498DB
    assert embed["fields"][0]["value"] == "**Pending Classification**"
    
    # User A
    txn = {"merchant": "M", "amount": "10", "classification": "A", "classified_by": "U"}
    embed = build_classification_embed(txn, config_users)
    assert embed["fields"][0]["value"] == "**Alice**"
    
    # User B
    txn = {"merchant": "M", "amount": "10", "classification": "B", "classified_by": "U"}
    embed = build_classification_embed(txn, config_users)
    assert embed["fields"][0]["value"] == "**Bob**"
    
    # Shared
    txn = {"merchant": "M", "amount": "10", "classification": "S", "classified_by": "U"}
    embed = build_classification_embed(txn, config_users)
    assert embed["fields"][0]["value"] == "**Shared (50/50)**"
    
    # Shared with percent
    txn = {"merchant": "M", "amount": "10", "classification": "S", "classified_by": "U", "percentage": "60"}
    embed = build_classification_embed(txn, config_users)
    assert embed["fields"][0]["value"] == "**Shared (60%)**"
    
    # With Note
    txn["note"] = "Test note"
    embed = build_classification_embed(txn, config_users)
    assert embed["fields"][-1]["name"] == "Note"
    assert embed["fields"][-1]["value"] == "Test note"

def test_send_transaction_notification(mocker, env_setup):
    mock_send = mocker.patch("lib.discord_client.send_message", return_value=True)
    txns = [{"transaction_id": "1", "merchant": "M", "amount": "10", "date": "2023-01-01"}]
    assert send_transaction_notification(txns) is True
    mock_send.assert_called_once()
    
    # Failure case
    mock_send.return_value = False
    assert send_transaction_notification(txns) is False

def test_send_settlement_notification(mocker, env_setup):
    mock_send = mocker.patch("lib.discord_client.send_message", return_value=True)
    assert send_settlement_notification("Message") is True
    mock_send.assert_called_once()

def test_send_error_notification(mocker, env_setup):
    mock_send = mocker.patch("lib.discord_client.send_message", return_value=True)
    assert send_error_notification("Error") is True
    mock_send.assert_called_once()
