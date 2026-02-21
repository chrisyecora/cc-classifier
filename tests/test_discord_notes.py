from lib import discord_client


def test_build_post_classification_components():
    txn_id = "txn_123"
    components = discord_client.build_post_classification_components(txn_id)

    assert len(components) == 1
    action_row = components[0]
    buttons = action_row["components"]

    # Expecting Undo and Add Note
    assert len(buttons) == 2

    undo_btn = buttons[0]
    assert undo_btn["label"] == "Undo"
    assert undo_btn["custom_id"] == "undo:txn_123"

    note_btn = buttons[1]
    assert note_btn["label"] == "Add Note"
    assert note_btn["custom_id"] == "note:txn_123"
    assert note_btn["style"] == 2  # Secondary (Grey)


def test_build_note_modal():
    txn_id = "txn_123"
    current_note = "Existing note"
    modal = discord_client.build_note_modal(txn_id, current_note)

    assert modal["title"] == "Add/Edit Note"
    assert modal["custom_id"] == "modal_note:txn_123"

    rows = modal["components"]
    assert len(rows) == 1

    text_input = rows[0]["components"][0]
    assert text_input["type"] == 4  # Text Input
    assert text_input["custom_id"] == "note_input"
    assert text_input["style"] == 2  # Paragraph
    assert text_input["value"] == "Existing note"
