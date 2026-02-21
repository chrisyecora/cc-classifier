import json
from lambdas.webhook import handle_undo, _process_exclude


def test_handle_undo_reset_fails(mocker, env_setup):
    mocker.patch("lambdas.webhook.reset_transaction", return_value=False)
    response = handle_undo({}, "txn1")
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Error: Could not undo" in body["data"]["content"]


def test_handle_undo_txn_not_found(mocker, env_setup):
    mocker.patch("lambdas.webhook.reset_transaction", return_value=True)
    mocker.patch("lambdas.webhook.get_transaction", return_value=None)
    response = handle_undo({}, "txn1")
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Error: Could not undo" in body["data"]["content"]


def test_handle_undo_success(mocker, env_setup):
    mocker.patch("lambdas.webhook.reset_transaction", return_value=True)
    mocker.patch(
        "lambdas.webhook.get_transaction",
        return_value={"merchant": "M", "amount": "10", "date": "2023", "transaction_id": "1"},
    )
    mocker.patch("lambdas.webhook.build_classification_components", return_value=[])
    response = handle_undo({}, "txn1")
    body = json.loads(response["body"])
    assert body["type"] == 7
    assert "New Transaction" in body["data"]["content"]


def test_process_exclude_fails(mocker, env_setup):
    mocker.patch("lambdas.webhook.exclude_transaction", return_value=False)
    response = _process_exclude({}, "txn1")
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Error: Could not exclude" in body["data"]["content"]


def test_process_exclude_txn_not_found_after(mocker, env_setup):
    mocker.patch("lambdas.webhook.exclude_transaction", return_value=True)
    mocker.patch("lambdas.webhook.get_transaction", return_value=None)
    response = _process_exclude({}, "txn1")
    body = json.loads(response["body"])
    assert body["type"] == 4
    assert "Transaction not found." in body["data"]["content"]
