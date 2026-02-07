import pytest
from lib.discord_client import send_message, verify_discord_signature
from config import get_config

def test_verify_discord_signature_valid(mocker, env_setup):
    # This requires generating a valid Ed25519 signature pair for test
    # Or mocking the VerifyKey.verify call.
    # Given we use pynacl directly, mocking VerifyKey is safer to avoid crypto complexity in tests.
    
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

def test_send_message_success(mocker, env_setup):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200
    
    test_channel = "999"
    success = send_message("Hello", channel_id=test_channel)
    assert success is True
    
    # Check if correct URL and headers were used
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
