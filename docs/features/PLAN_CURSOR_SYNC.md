

# Plan: Implement Plaid Cursor-based Sync

**Goal:** Transition from date-based transaction fetching to cursor-based fetching (`/transactions/sync`) to ensure reliable data synchronization without gaps or duplicates, even if the system is down for extended periods.

---

## 1. Storage Layer Updates (`lib/storage.py`)

We need a place to persist the `next_cursor` returned by Plaid. S3 is our storage, so we can either:
A. Add a metadata file `cursor.txt`.
B. Store it in a separate CSV/JSON.
C. (Chosen) Simple text file `plaid_cursor.txt` in the same S3 bucket.

### Tasks:
1.  **Test:** Create `tests/test_storage_cursor.py`.
    *   Test `save_cursor(cursor_str)`.
    *   Test `get_cursor()` -> returns cursor or `None` if missing.
2.  **Implement:** Add `save_cursor` and `get_cursor` to `lib/storage.py`.

## 2. Plaid Client Updates (`lib/plaid_client.py`)

Refactor `fetch_transactions` to accept an optional `cursor` argument instead of start/end dates.

### Tasks:
1.  **Test:** Update `tests/test_plaid_client.py`.
    *   Test `fetch_new_transactions(cursor)` calls `transactions_sync` with the provided cursor.
    *   Test it returns `(transactions, new_cursor)`.
    *   Test pagination handling (looping while `has_more` is true).
2.  **Implement:**
    *   Rename/Refactor `fetch_transactions` to `fetch_new_transactions(cursor: str | None) -> tuple[list[dict], str]`.
    *   Remove date range logic.
    *   Use the cursor in `TransactionsSyncRequest`.

## 3. Daily Scan Handler Updates (`lambdas/daily_scan.py`)

Update the orchestration logic to read the cursor, fetch, and save the new cursor.

### Tasks:
1.  **Test:** Update `tests/test_daily_scan.py`.
    *   Mock `get_cursor` to return "old_cursor".
    *   Mock `fetch_new_transactions` to return `(txns, "new_cursor")`.
    *   Verify `save_cursor("new_cursor")` is called after successful fetch/save.
2.  **Implement:**
    *   Read cursor from storage.
    *   Call `fetch_new_transactions`.
    *   Append transactions to S3.
    *   Save new cursor to S3.
    *   Send notifications.

## 4. Migration / Backwards Compatibility
*   On first run, `get_cursor` will return `None`.
*   Plaid treats `cursor=None` as "fetch from beginning" or "fetch recent"?
*   **Critical:** If we start with `null` cursor, Plaid might return *all* history. We should probably handle the initial state carefully or allow a manual "seed" of the cursor.
*   **Refinement:** For the first run, if no cursor exists, maybe we fetch the last 30 days (like before) and get the cursor from that response?
    *   Actually, `/transactions/sync` works best if you just start tracking. If cursor is empty, it might give a lot of data.
    *   Better approach: `fetch_new_transactions` handles the "initial sync" logic. If cursor is empty, maybe we accept it fetches everything, or we filter duplicates (which `append_transactions` already does). `append_transactions` deduplicates by ID, so fetching history is safe (just potentially slow/costly on tokens).
    *   Let's rely on `append_transactions` deduplication.

---

## Step-by-Step Execution

1.  **Storage:** Tests + Impl for `plaid_cursor.txt`.
2.  **Plaid:** Tests + Impl for cursor-based fetch.
3.  **Handler:** Wiring it up.
