import pytest
from lib.twilio_client import (
    send_sms, 
    format_transaction_list,
    send_transaction_notification
)

def test_format_transaction_list():
    txns = [
        {"merchant": "Target", "amount": "50.00"},
        {"merchant": "Uber", "amount": "15.25"}
    ]
    
    msg = format_transaction_list(txns)
    
    assert "1. Target $50.00" in msg
    assert "2. Uber $15.25" in msg
    assert "Reply format:" in msg

def test_send_sms_success(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.twilio_client.get_twilio_client", return_value=mock_client)
    
    # Mock message creation
    mock_msg = mocker.MagicMock()
    mock_msg.sid = "SM123"
    mock_client.messages.create.return_value = mock_msg
    
    success = send_sms("+15551111111", "Hello")
    
    assert success is True
    mock_client.messages.create.assert_called_once_with(
        to="+15551111111",
        from_="+15550000000", # From env_setup
        body="Hello"
    )

def test_send_sms_retry_failure(mocker, env_setup):
    mock_client = mocker.MagicMock()
    mocker.patch("lib.twilio_client.get_twilio_client", return_value=mock_client)
    
    from twilio.base.exceptions import TwilioRestException
    # Fail twice (original + retry)
    mock_client.messages.create.side_effect = TwilioRestException(500, "uri", "msg")
    
    success = send_sms("+15551111111", "Hello")
    
    assert success is False
    assert mock_client.messages.create.call_count == 2

def test_send_transaction_notification(mocker, env_setup):
    mock_send = mocker.patch("lib.twilio_client.send_sms", return_value=True)
    
    users = {
        "user_a": {"phone": "+1A"},
        "user_b": {"phone": "+1B"}
    }
    txns = [{"merchant": "Test", "amount": "10.00"}]
    
    send_transaction_notification(txns, users)
    
    assert mock_send.call_count == 2
    # Check calls
    # any_order=True if strict order doesn't matter
    calls = mock_send.call_args_list
    phones = [c[0][0] for c in calls]
    assert "+1A" in phones
    assert "+1B" in phones

def test_format_transaction_list_empty():
    msg = format_transaction_list([])
    assert msg == ""
