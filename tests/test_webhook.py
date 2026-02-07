import pytest
from lambdas.webhook import handler
from lib.parser import ParseResult, Classification

def test_webhook_handler_success(mocker, env_setup):
    # Mock dependencies
    mocker.patch("lambdas.webhook.read_users", return_value={
        "user_a": {"phone": "+15551111111", "name": "Alex"},
        "user_b": {"phone": "+15552222222", "name": "Beth"}
    })
    mocker.patch("lambdas.webhook.get_user_by_phone", return_value={
        "id": "user_a", "name": "Alex", "phone": "+15551111111"
    })
    
    # Mock parser
    mock_parse = mocker.patch("lambdas.webhook.parse_reply", return_value=ParseResult(
        classifications=[Classification(1, "S", 70)],
        errors=[]
    ))
    
    # Mock storage
    mocker.patch("lambdas.webhook.get_unclassified_transactions", return_value=[
        {"transaction_id": "tx1", "merchant": "Target"} # Index 1 (0-based idx 0)
    ])
    mock_update = mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    mocker.patch("lambdas.webhook.get_other_user", return_value={"phone": "+1B"})
    
    # Mock notifications
    mock_confirm = mocker.patch("lambdas.webhook.send_classification_confirmation")
    mock_notify = mocker.patch("lambdas.webhook.send_classification_notification")
    
    # Run handler
    # Event form-encoded body "Body=1S70&From=%2B15551111111"
    event = {
        "body": "Body=1S70&From=%2B15551111111",
        "isBase64Encoded": False
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    assert "<Response>" in response["body"]
    # Check for confirmation in body (simplified check)
    assert "Shared" in response["body"] 
    
    mock_update.assert_called_once()
    # mock_confirm.assert_called_once() # We use TwiML now
    mock_notify.assert_called_once()

def test_webhook_unknown_user(mocker, env_setup):
    mocker.patch("lambdas.webhook.get_user_by_phone", return_value=None)
    
    event = {
        "body": "Body=Hello&From=%2B19999999999"
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 403 # Or 200 with empty? Usually 403 or ignore.
    # Let's say 403 Forbidden

def test_webhook_parse_error(mocker, env_setup):
    mocker.patch("lambdas.webhook.get_user_by_phone", return_value={"id": "user_a"})
    mocker.patch("lambdas.webhook.get_unclassified_transactions", return_value=[
        {"transaction_id": "tx1"}
    ])
    
    mocker.patch("lambdas.webhook.parse_reply", return_value=ParseResult(
        classifications=[],
        errors=["invalid"]
    ))
    
    # Mock format error
    mocker.patch("lambdas.webhook.format_error_response", return_value="Error msg")
    
    event = {"body": "Body=invalid&From=%2B1A"}
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    assert "Error msg" in response["body"]

def test_webhook_invalid_transaction_number(mocker, env_setup):
    mocker.patch("lambdas.webhook.get_user_by_phone", return_value={"id": "user_a"})
    # Only 1 unclassified transaction
    mocker.patch("lambdas.webhook.get_unclassified_transactions", return_value=[
        {"transaction_id": "tx1"}
    ])
    
    # User replies "2S" (index 2, but only 1 exists)
    mocker.patch("lambdas.webhook.parse_reply", return_value=ParseResult(
        classifications=[Classification(2, "S", None)],
        errors=[]
    ))
    
    mock_format_invalid = mocker.patch("lambdas.webhook.format_invalid_transaction_response", return_value="Invalid range")
    
    event = {"body": "Body=2S&From=%2B1A"}
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    assert "Invalid range" in response["body"]
    mock_format_invalid.assert_called_with(2, 1)
