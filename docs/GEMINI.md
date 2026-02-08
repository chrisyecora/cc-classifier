# Gemini Context: Credit Card Tracker (cc-classifier)

## Project Overview
**Goal:** Develop an SMS-based credit card expense tracker for two users sharing a card. The system automatically fetches transactions from Plaid, prompts users via SMS to classify them (Shared, User A, User B), and calculates monthly settlements.

**Architecture:** Serverless application on AWS using Lambda, S3 (CSV storage), API Gateway, and EventBridge.
**Stack:** Python 3.11, AWS SAM (Infrastructure as Code), Twilio (SMS), Plaid (Banking API).

## Current Status
**Phase:** Ready for Deployment.
**Artifacts:** Application code, tests, and SAM template are complete. `sam build` passes.

## Development Conventions

### Tech Stack & Tools
*   **Runtime:** Python 3.11+
*   **Infrastructure:** AWS SAM (`template.yaml`)
*   **Testing:** `pytest` using `pytest-mock` and a custom in-memory S3 mock (avoiding `moto` due to compatibility issues).
*   **Linting/Formatting:** (Standard Python tooling).

### Architecture Structure
*   `lambdas/`: AWS Lambda function handlers (`daily_scan.py`, `webhook.py`).
*   `lib/`: Core business logic and clients (`plaid_client.py`, `discord_client.py`, `storage.py`, `settlement.py`).
*   `tests/`: Unit and integration tests.
*   `config.py`: Environment variable management.

### Key Workflows
*   **Transaction Flow:** Plaid -> Lambda (Daily) -> S3 CSV -> Discord Webhook -> User Button Click -> Discord Interaction -> Lambda -> Update S3 CSV.
*   **Settlement:** Monthly calculation (10th-9th billing cycle) triggered by EventBridge.

## Building & Running

*   **Build:** `sam build`
*   **Test:** `pytest` (or `PYTHONPATH=. .venv/bin/pytest`)
*   **Deploy:** `sam deploy --guided` (first time), `sam deploy` (subsequent)

## Reference
See `PROJECT_SPECIFICATION.md` for:
*   Detailed Data Schemas (CSV columns)
*   SMS Protocol (Formats for requests and replies)
*   Environment Variables list
*   Test Coverage Requirements
