import pytest

from lambdas.admin_api import publish, update_transaction
from lib.statements import ConflictError, save_period, statement_view
from lib.storage import (
    exclude_transaction,
    get_transaction,
    reset_transaction,
    update_transaction as discord_classify,
    update_transaction_note,
    write_transactions,
)


def transaction(id, posted, amount="10.00", classification="A"):
    return {
        "transaction_id": id,
        "date": posted,
        "amount": amount,
        "merchant": id,
        "classification": classification,
        "excluded": "",
        "note": "",
    }


def test_admin_reclassifies_and_rejects_stale_edit(dynamodb_mock):
    write_transactions([transaction("one", "2026-09-01")])
    body = {
        "version": 0,
        "classification": "S",
        "percentage": "75",
        "share_user": "A",
        "excluded": False,
        "note": "Reviewed",
    }
    updated = update_transaction("one", body)
    assert updated["percentage"] == "75"
    assert updated["note"] == "Reviewed"
    assert updated["edit_version"] == 1
    with pytest.raises(ConflictError, match="changed"):
        update_transaction("one", body)


def test_discord_actions_advance_edit_version_and_reject_stale_admin_save(dynamodb_mock):
    write_transactions([transaction("one", "2026-09-01", classification="")])
    stale_body = {
        "version": 0,
        "classification": "A",
        "percentage": None,
        "share_user": None,
        "excluded": False,
        "note": "",
    }

    assert discord_classify("one", "A", "TestAlex", None)
    assert get_transaction("one")["edit_version"] == 1
    with pytest.raises(ConflictError, match="changed"):
        update_transaction("one", stale_body)

    assert update_transaction_note("one", "From Discord")
    assert get_transaction("one")["edit_version"] == 2
    assert exclude_transaction("one")
    assert get_transaction("one")["edit_version"] == 3
    assert reset_transaction("one")
    assert get_transaction("one")["edit_version"] == 4


def test_publish_then_revision_and_failed_discord(dynamodb_mock, mocker):
    write_transactions([transaction("one", "2026-09-01")])
    save_period("2026-09", "2026-08-12", "2026-09-09", 0)
    first = statement_view("2026-09")
    send = mocker.patch("lambdas.admin_api.send_settlement_notification", return_value=False)
    with pytest.raises(RuntimeError, match="Discord"):
        publish("2026-09", first["version"])
    assert statement_view("2026-09")["revision"] == 0
    send.return_value = True
    published = publish("2026-09", first["version"])
    assert published["revision"] == 1
    assert not published["has_unpublished_changes"]
    update_transaction(
        "one",
        {"version": 0, "classification": "B", "percentage": None, "share_user": None, "excluded": False, "note": ""},
    )
    changed = statement_view("2026-09")
    assert changed["has_unpublished_changes"]
    revised = publish("2026-09", changed["version"])
    assert revised["revision"] == 2
    assert "revision 2" in send.call_args.args[0]


def test_publish_uses_current_rows_and_ignores_note_only_edits(dynamodb_mock, mocker):
    write_transactions([transaction("one", "2026-09-01")])
    save_period("2026-09", "2026-08-12", "2026-09-09", 0)
    reviewed = statement_view("2026-09")
    update_transaction(
        "one",
        {"version": 0, "classification": "B", "percentage": None, "share_user": None, "excluded": False, "note": ""},
    )
    send = mocker.patch("lambdas.admin_api.send_settlement_notification")
    published = publish("2026-09", reviewed["version"])
    assert published["published"]["totals"] == published["totals"]
    assert published["totals"] != reviewed["totals"]
    send.assert_called_once()
    update_transaction_note("one", "Reviewed")
    assert not statement_view("2026-09")["has_unpublished_changes"]
