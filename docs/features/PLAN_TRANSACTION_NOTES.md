# Plan: Transaction Notes Feature

**Goal:** Allow users to add custom text notes to transactions after they have been classified. This provides context for expenses (e.g., "Dinner with client", "Groceries for party") and is saved persistently in the CSV data.

---

## 1. Storage Layer Updates (`lib/storage.py`)

We need to persist the note in the existing CSV structure.

### Tasks:
1.  **Schema Update:**
    *   Add `note` to `CSV_FIELDNAMES`.
    *   *Assumption:* The CSV is starting from scratch, so no migration logic for existing rows is needed.
2.  **Tests (TDD):**
    *   Create or update `tests/test_storage.py` (or a new test file) to:
        *   Test `update_transaction_note` persists data correctly.
        *   Test `reset_transaction` clears the note.
        *   Test reading/writing transactions includes the new `note` field.
3.  **Implementation:**
    *   Implement `update_transaction_note(transaction_id, note)`.
    *   Update `reset_transaction(transaction_id)` to clear the note.

## 2. Interaction Handler Updates (`lambdas/webhook.py`)

We need to add UI controls for adding notes and handling the user input.

### Tasks:
1.  **Tests (TDD):**
    *   Create a test case in `tests/test_webhook.py` that simulates:
        *   Clicking the "Add Note" button (verifying Modal response).
        *   Submitting the Modal (verifying storage update and message edit).
2.  **UI Updates (`lib/discord_client.py`):**
    *   Update `build_classification_components` to include a "Add Note" button.
    *   Button ID: `note:{transaction_id}`.
3.  **Implementation:**
    *   Handle `note:...` button click: Return Modal (`type: 9`).
    *   Handle `modal_note:...` submission: Call `storage.update_transaction_note` and refresh Discord message.

## 3. Discord Client Updates (`lib/discord_client.py`)

Refactor message construction to include notes.

### Tasks:
1.  **Tests (TDD):**
    *   Verify message builder includes the note text when present.
2.  **Implementation:**
    *   Update message formatting logic to append `\n📝 Note: ...` if a note exists.

---

## Step-by-Step Execution

1.  **Storage TDD:** Write tests for storage updates -> Implement storage changes.
2.  **Discord/Webhook TDD:** Write tests for interaction flow -> Implement UI and Webhook logic.
3.  **Verify:** Run all tests to ensure green suite.
