import pytest
import json
from lambdas import webhook


@pytest.fixture
def mock_update(mocker):
    return mocker.patch("lambdas.webhook.update_transaction")


@pytest.fixture
def mock_update_note(mocker):
    # We will import update_transaction_note in webhook.py
    return mocker.patch("lambdas.webhook.update_transaction_note")


def test_handle_note_button_click(mocker):
    # Simulate clicking "Add Note"
    interaction = {
        "type": 3,
        "data": {"component_type": 2, "custom_id": "note:txn_123"},
        "member": {"user": {"username": "UserA"}},
    }

    # Mock finding transaction to get existing note
    mocker.patch("lambdas.webhook.get_transaction", return_value={"transaction_id": "txn_123", "note": "Existing"})

    response = webhook.handle_button_click(interaction)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 9  # Modal

    modal_data = body["data"]
    assert modal_data["custom_id"] == "modal_note:txn_123"
    assert modal_data["components"][0]["components"][0]["value"] == "Existing"


def test_handle_note_modal_submit(mock_update_note, mocker):
    # Simulate submitting modal
    interaction = {
        "type": 5,
        "data": {"custom_id": "modal_note:txn_123", "components": [{"components": [{"value": "New Note Content"}]}]},
        "member": {"user": {"username": "UserA"}},
        "message": {"content": "Original Message"},
    }

    # Mock transaction read (returning the state AFTER update)
    mocker.patch(
        "lambdas.webhook.get_transaction",
        return_value={
            "transaction_id": "txn_123",
            "classification": "S",
            "classified_by": "UserA",
            "amount": "100",
            "merchant": "Test",
            "date": "2023-01-01",
            "note": "New Note Content",  # Simulating the update
        },
    )

    # Mock user config
    mocker.patch(
        "lambdas.webhook.read_users", return_value={"user_a": {"name": "User A"}, "user_b": {"name": "User B"}}
    )

    response = webhook.handle_modal_submit(interaction)

    # Verify update called
    mock_update_note.assert_called_with("txn_123", "New Note Content")

    # Verify response updates message
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["type"] == 7  # Update Message

    # Content should be empty as we use embeds now
    assert body["data"].get("content") == ""

    embeds = body["data"]["embeds"]
    assert len(embeds) == 1
    fields = embeds[0]["fields"]

    # Check for Note field
    note_field = next((f for f in fields if f["name"] == "Note"), None)
    assert note_field is not None
    assert "New Note Content" in note_field["value"]

    # Check for User info
    by_field = next((f for f in fields if f["name"] == "By"), None)
    assert by_field is not None
    assert "UserA" in by_field["value"]
