import json
from lambdas.webhook import handler, handle_modal_submit

# --- Existing Tests (Buttons/Menus) ---


def test_webhook_invalid_signature(mocker):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=False)
    event = {"headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"}, "body": "body"}
    response = handler(event, None)
    assert response["statusCode"] == 401


def test_webhook_ping(mocker):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    event = {"headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"}, "body": json.dumps({"type": 1})}
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["type"] == 1


def test_webhook_button_click_success(mocker):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    mock_update = mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    mocker.patch("lambdas.webhook.read_users", return_value={"user_a": {"name": "A"}, "user_b": {"name": "B"}})

    # Mock get_transaction for the reload in _process_update
    txn_data = {
        "transaction_id": "tx1",
        "classification": "S",
        "classified_by": "Chris",
        "amount": "100",
        "merchant": "Test",
        "date": "2023-01-01",
    }
    mocker.patch("lambdas.webhook.get_transaction", return_value=txn_data)

    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps(
            {
                "type": 3,
                "data": {"custom_id": "classify:tx1:S", "component_type": 2},
                "member": {"user": {"username": "Chris"}},
            }
        ),
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    mock_update.assert_called()

    body = json.loads(response["body"])
    assert "embeds" in body["data"]
    embed = body["data"]["embeds"][0]
    assert embed["title"] == "Test"
    assert "Classified As" in embed["fields"][0]["name"]


def test_webhook_button_click_already_classified(mocker):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    mocker.patch("lambdas.webhook.update_transaction", return_value=False)
    mocker.patch("lambdas.webhook.read_users", return_value={"user_a": {"name": "A"}, "user_b": {"name": "B"}})

    # Mock get_transaction
    txn_data = {
        "transaction_id": "tx1",
        "classification": "S",
        "classified_by": "Chris",
        "amount": "100",
        "merchant": "Test",
        "date": "2023-01-01",
    }
    mocker.patch("lambdas.webhook.get_transaction", return_value=txn_data)

    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps(
            {
                "type": 3,
                "data": {"custom_id": "classify:tx1:S", "component_type": 2},
                "member": {"user": {"username": "Chris"}},
            }
        ),
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    # Even if already classified, we now return the update response (type 7) to refresh the UI
    body = json.loads(response["body"])
    assert body["type"] == 7
    assert "embeds" in body["data"]


def test_webhook_select_menu_success(mocker):
    mocker.patch("lambdas.webhook.verify_discord_signature", return_value=True)
    mock_update = mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    mocker.patch("lambdas.webhook.read_users", return_value={"user_a": {"name": "A"}, "user_b": {"name": "B"}})

    txn_data = {
        "transaction_id": "tx1",
        "classification": "S",
        "classified_by": "Chris",
        "amount": "100",
        "merchant": "Test",
        "date": "2023-01-01",
        "percentage": "70",
    }
    mocker.patch("lambdas.webhook.get_transaction", return_value=txn_data)

    event = {
        "headers": {"x-signature-ed25519": "sig", "x-signature-timestamp": "ts"},
        "body": json.dumps(
            {
                "type": 3,
                "data": {"custom_id": "classify_split:tx1", "component_type": 3, "values": ["S70"]},
                "member": {"user": {"username": "Chris"}},
            }
        ),
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    mock_update.assert_called_with("tx1", "S", "Chris", 70.0)


# --- New Modal Tests ---


def test_modal_custom_amount_expense(mocker):
    """Test valid positive expense logic ($20 of $50)."""
    # Mock get_transaction
    txn_data = {
        "transaction_id": "tx1",
        "amount": "50.00",
        "classification": "S",
        "classified_by": "Chris",
        "merchant": "Test",
        "date": "2023-01-01",
    }
    mocker.patch("lambdas.webhook.get_transaction", return_value=txn_data)

    mock_update = mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    mocker.patch("lambdas.webhook.read_users", return_value={"user_a": {"name": "A"}, "user_b": {"name": "B"}})

    interaction = {
        "type": 5,  # MODAL_SUBMIT
        "data": {"custom_id": "modal_custom_amount:tx1", "components": [{"components": [{"value": "20.00"}]}]},
        "member": {"user": {"username": "Chris"}},
    }

    response = handle_modal_submit(interaction)

    assert response["statusCode"] == 200
    # 20 / 50 = 40%
    mock_update.assert_called_with("tx1", "S", "Chris", 40.0)


def test_modal_custom_amount_credit(mocker):
    """Test valid negative credit logic (-$20 of -$50)."""
    txn_data = {
        "transaction_id": "tx1",
        "amount": "-50.00",
        "classification": "S",
        "classified_by": "Chris",
        "merchant": "Test",
        "date": "2023-01-01",
    }
    mocker.patch("lambdas.webhook.get_transaction", return_value=txn_data)

    mock_update = mocker.patch("lambdas.webhook.update_transaction", return_value=True)
    mocker.patch("lambdas.webhook.read_users", return_value={"user_a": {"name": "A"}, "user_b": {"name": "B"}})

    interaction = {
        "type": 5,
        "data": {"custom_id": "modal_custom_amount:tx1", "components": [{"components": [{"value": "-20.00"}]}]},
        "member": {"user": {"username": "Chris"}},
    }

    response = handle_modal_submit(interaction)

    assert response["statusCode"] == 200
    # -20 / -50 = 0.4 -> 40% (positive percentage of negative total)
    mock_update.assert_called_with("tx1", "S", "Chris", 40.0)


def test_modal_custom_amount_invalid_expense(mocker):
    """Test invalid input > total ($60 of $50)."""
    mocker.patch("lambdas.webhook.get_transaction", return_value={"transaction_id": "tx1", "amount": "50.00"})

    interaction = {
        "type": 5,
        "data": {"custom_id": "modal_custom_amount:tx1", "components": [{"components": [{"value": "60.00"}]}]},
        "member": {"user": {"username": "Chris"}},
    }

    response = handle_modal_submit(interaction)

    assert response["statusCode"] == 200  # Returns error message to Discord (200 OK with error content)
    body = json.loads(response["body"])
    assert body["type"] == 4  # RESPONSE_TYPE_CHANNEL_MESSAGE_WITH_SOURCE
    assert "Amount must be between" in body["data"]["content"]


def test_modal_custom_amount_invalid_credit_mixed_sign(mocker):
    """Test invalid input (positive input $20 for credit -$50)."""
    mocker.patch("lambdas.webhook.get_transaction", return_value={"transaction_id": "tx1", "amount": "-50.00"})

    interaction = {
        "type": 5,
        "data": {"custom_id": "modal_custom_amount:tx1", "components": [{"components": [{"value": "20.00"}]}]},
        "member": {"user": {"username": "Chris"}},
    }

    response = handle_modal_submit(interaction)

    body = json.loads(response["body"])
    assert "Amount must be between" in body["data"]["content"]


def test_modal_custom_amount_invalid_credit_too_large(mocker):
    """Test invalid input (-$60 for credit -$50)."""
    mocker.patch("lambdas.webhook.get_transaction", return_value={"transaction_id": "tx1", "amount": "-50.00"})

    interaction = {
        "type": 5,
        "data": {"custom_id": "modal_custom_amount:tx1", "components": [{"components": [{"value": "-60.00"}]}]},
        "member": {"user": {"username": "Chris"}},
    }

    response = handle_modal_submit(interaction)

    body = json.loads(response["body"])
    assert "Amount must be between" in body["data"]["content"]
