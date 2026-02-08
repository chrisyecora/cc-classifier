
import pytest
import json
from lambdas import webhook

def test_json_response_supports_embeds():
    resp = webhook.json_response(7, embeds=[{"title": "Test"}])
    body = json.loads(resp["body"])
    assert "embeds" in body["data"]
    assert body["data"]["embeds"][0]["title"] == "Test"

def test_build_update_response_uses_embed(mocker):
    # Mock data
    interaction = {}
    txn = {
        "transaction_id": "txn_123",
        "merchant": "Test Merchant",
        "amount": "100.00",
        "date": "2023-01-01",
        "classification": "S",
        "classified_by": "UserA",
        "note": "My Note"
    }
    
    # Mock users
    mocker.patch("lambdas.webhook.read_users", return_value={
        "user_a": {"name": "User A"},
        "user_b": {"name": "User B"}
    })
    
    # Mock components builder
    mocker.patch("lambdas.webhook.build_post_classification_components", return_value=[])
    
    # Execute
    resp = webhook._build_update_response(interaction, txn, updated=True)
    body = json.loads(resp["body"])
    data = body["data"]
    
    # Verify Embed
    assert "embeds" in data
    embed = data["embeds"][0]
    
    assert embed["title"] == "Test Merchant"
    assert "$100.00" in embed["description"]
    assert "2023-01-01" in embed["description"]
    assert embed["color"] == 5763719 # 0x57F287 (Green)
    
    fields = embed["fields"]
    assert len(fields) == 3 # Class, By, Note
    
    assert fields[0]["name"] == "Classified As"
    assert "Shared (50/50)" in fields[0]["value"]
    
    assert fields[1]["name"] == "By"
    assert "UserA" in fields[1]["value"]
    
    assert fields[2]["name"] == "Note"
    assert "My Note" in fields[2]["value"]
