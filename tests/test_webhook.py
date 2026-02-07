import json
import pytest
from lambdas.webhook import handler

def test_webhook_invalid_signature(mocker, env_setup):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=False)
    
    event = {
        "headers": {
            "x-signature-ed25519": "sig",
            "x-signature-timestamp": "ts"
        },
        "body": "body"
    }
    
    response = handler(event, None)
    assert response["statusCode"] == 401

def test_webhook_ping(mocker, env_setup):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    
    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps({"type": 1}) # PING
    }
    
    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 1 # PONG

def test_webhook_button_click_success(mocker, env_setup):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    
    # Mock storage
    mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    # We might need to mock read_users if we use names, but here we pass raw S/A/B
    
    # Custom ID: classify:tx1:S
    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps({
            "type": 3, # MESSAGE_COMPONENT
            "data": {"custom_id": "classify:tx1:S"},
            "member": {"user": {"username": "Chris"}}
        })
    }
    
    response = handler(event, None)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    
    # Type 7 = Update Message (preferred to remove buttons) or Type 4 = New Message
    assert body["type"] == 7 
    assert "Shared" in body["data"]["content"]
    assert body["data"]["components"] == [] # Verify buttons are removed

def test_webhook_button_click_already_classified(mocker, env_setup):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    mocker.patch("lambdas.webhook.update_transaction", return_value=False)
    
    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps({
            "type": 3, 
            "data": {"custom_id": "classify:tx1:S"},
            "member": {"user": {"username": "Chris"}}
        })
    }
    
    response = handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "already classified" in body["data"]["content"]