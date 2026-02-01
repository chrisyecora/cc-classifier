# Gemini Context: Credit Card Tracker (cc-classifier)

## Project Overview
**Goal:** Develop an SMS-based credit card expense tracker for two users sharing a card. The system automatically fetches transactions from Plaid, prompts users via SMS to classify them (Shared, User A, User B), and calculates monthly settlements.

**Architecture:** Serverless application on AWS using Lambda, S3 (CSV storage), API Gateway, and EventBridge.
**Stack:** Python 3.11, AWS SAM (Infrastructure as Code), Twilio (SMS), Plaid (Banking API).

## Current Status
**Phase:** Initialization / implementation.
**Artifacts:** `PROJECT_SPECIFICATION.md` contains the complete, detailed requirements and architecture. The codebase is currently being scaffolded based on these specs.

## Development Conventions

### Tech Stack & Tools
*   **Runtime:** Python 3.11
*   **Infrastructure:** AWS SAM (`template.yaml`)
*   **Testing:** `pytest` using `pytest-mock` and a custom in-memory S3 mock (avoiding `moto` due to compatibility issues).
*   **Linting/Formatting:** (Pending setup, likely `ruff` or `black` + `flake8`).

### Architecture Structure
*   `lambdas/`: AWS Lambda function handlers (`daily_scan.py`, `webhook.py`).
*   `lib/`: Core business logic and clients (`plaid_client.py`, `twilio_client.py`, `storage.py`, `parser.py`, `settlement.py`).
*   `tests/`: Unit and integration tests.
*   `config.py`: Environment variable management.

### Key Workflows
*   **Transaction Flow:** Plaid -> Lambda (Daily) -> S3 CSV -> Twilio SMS -> User Reply -> Twilio Webhook -> Lambda -> Update S3 CSV.
*   **Settlement:** Monthly calculation (10th-9th billing cycle) triggered by EventBridge.

## Building & Running
(Note: These commands will be valid once the project is scaffolded)

*   **Build:** `sam build`
*   **Test:** `pytest`
*   **Deploy:** `sam deploy --guided` (first time), `sam deploy` (subsequent)

## Reference
See `PROJECT_SPECIFICATION.md` for:
*   Detailed Data Schemas (CSV columns)
*   SMS Protocol (Formats for requests and replies)
*   Environment Variables list
*   Test Coverage Requirements
