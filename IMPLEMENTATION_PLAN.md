# Implementation Plan: Credit Card Tracker

This plan outlines the step-by-step implementation of the Credit Card Tracker using a Test-Driven Development (TDD) approach.

**Guiding Principles:**
1.  **TDD:** Write the test `tests/test_foo.py` *before* the implementation `lib/foo.py`.
2.  **Mocking:** Use `unittest.mock` and `pytest` fixtures. Do not rely on live AWS/Plaid/Twilio APIs during tests.
3.  **Atomic Steps:** Complete one component fully (tests + code) before moving to the next.

---

## Phase 0: Project Initialization & Infrastructure

**Goal:** Set up the file structure, environment configuration, and testing harness.

1.  **Scaffold Directory Structure**
    *   Create directories: `lambdas/`, `lib/`, `tests/`.
    *   Create root files: `requirements.txt`, `pytest.ini`, `config.py`.

2.  **Define Dependencies**
    *   Update `requirements.txt` with: `boto3`, `twilio`, `plaid-python`, `pytest`, `pytest-mock`.

3.  **Environment & Config**
    *   Implement `config.py` to read from environment variables.
    *   **Test:** Create `tests/test_config.py` to verify `get_config()` reads env vars correctly and uses defaults.

4.  **Testing Harness (Crucial)**
    *   Create `tests/conftest.py`.
    *   **Action:** Implement `InMemoryS3` class here to mock S3 behavior (put/get object).
    *   **Fixture:** Create `s3_mock` fixture that patches `boto3.client` to use `InMemoryS3`.
    *   **Fixture:** Create `env_setup` to inject dummy env vars for tests.

---

## Phase 1: Core Logic & Storage (No External APIs)

**Goal:** Implement the "brain" of the application: parsing, math, and data persistence.

### 1.1 SMS Parser (`lib/parser.py`)
*   **Test (`tests/test_parser.py`):**
    *   Test standard inputs: `1S`, `2A`, `3S70`.
    *   Test case insensitivity: `1s`, `2a`.
    *   Test invalid inputs: `invalid`, `4X`.
    *   Test multiple lines.
*   **Implement:** `lib/parser.py` with `parse_reply`, `parse_line`.

### 1.2 Settlement Logic (`lib/settlement.py`)
*   **Test (`tests/test_settlement.py`):**
    *   Test basic splits (50/50).
    *   Test custom percentages (e.g., 70/30).
    *   Test individual assignments (100% User A).
    *   Test rounding logic (currency).
*   **Implement:** `lib/settlement.py` with `calculate_settlement`.

### 1.3 Storage Layer (`lib/storage.py`)
*   **Test (`tests/test_storage.py`):**
    *   Test `read_transactions` (parse CSV from mock S3).
    *   Test `write_transactions` (convert list to CSV and put to mock S3).
    *   Test `append_transactions` (handle duplicates based on `transaction_id`).
    *   Test `update_transaction` (modify existing row).
    *   Test `get_statement_period` (date math for 10th-9th cycle).
*   **Implement:** `lib/storage.py` using `boto3` (which will be mocked by `conftest.py`).

---

## Phase 2: External Client Wrappers

**Goal:** implement wrappers for Plaid and Twilio. We will mock the *libraries* (`plaid-python`, `twilio`) in our tests.

### 2.1 Plaid Client (`lib/plaid_client.py`)
*   **Test (`tests/test_plaid_client.py`):**
    *   Mock `plaid.api.plaid_api.PlaidApi`.
    *   Test `fetch_transactions` handles pagination (if applicable) and transformation.
    *   Test retry logic (simulate API exception).
*   **Implement:** `lib/plaid_client.py`.

### 2.2 Twilio Client (`lib/twilio_client.py`)
*   **Test (`tests/test_twilio_client.py`):**
    *   Mock `twilio.rest.Client`.
    *   Test `send_sms` calls `messages.create`.
    *   Test `format_transaction_list` string generation.
*   **Implement:** `lib/twilio_client.py`.

---

## Phase 3: Lambda Handlers (Integration)

**Goal:** Wire everything together in the entry points.

### 3.1 Daily Scan Handler (`lambdas/daily_scan.py`)
*   **Test (`tests/test_daily_scan.py`):**
    *   **Case 1 (Daily):** Mock `fetch_transactions` to return data. Verify `append_transactions` is called and `send_sms` is triggered.
    *   **Case 2 (Monthly):** Simulate event with "MonthlySettlement" resource. Verify `calculate_settlement` and `send_sms` are called.
*   **Implement:** `lambdas/daily_scan.py`.

### 3.2 Webhook Handler (`lambdas/webhook.py`)
*   **Test (`tests/test_webhook.py`):**
    *   Mock API Gateway event structure (body with `From` and `Body`).
    *   Mock `read_users` to validate sender.
    *   Mock `parse_reply`.
    *   Mock `update_transaction`.
    *   Verify correct TwiML response is returned.
*   **Implement:** `lambdas/webhook.py`.

---

## Phase 4: Infrastructure & Deployment

**Goal:** Define AWS resources and deploy.

1.  **SAM Template**
    *   Create/Update `template.yaml` matching the specs (EventBridge rules, API Gateway, DynamoDB/S3 permissions).

2.  **Build & Verify**
    *   Run `sam build`.
    *   Run full test suite: `pytest`.

3.  **Deploy**
    *   Run `sam deploy --guided`.
    *   Manual verification (if possible/needed).

---

## Phase 5: Documentation & Polish

1.  Update `README.md` with usage instructions.
2.  Ensure `GEMINI.md` is up to date with any architectural changes made during dev.
