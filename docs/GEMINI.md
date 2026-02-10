# Gemini Context: Credit Card Tracker (cc-classifier)

## Project Overview
**Goal:** Develop a Discord-based credit card expense tracker for two users sharing a card. The system automatically fetches transactions from Plaid, prompts users via Discord interactive messages to classify them (Shared, User A, User B, Custom Split, Ignore), and calculates monthly settlements.

**Architecture:** Serverless application on AWS using Lambda, DynamoDB (NoSQL), API Gateway, and EventBridge.
**Stack:** Python 3.11, AWS SAM (Infrastructure as Code), Discord API (Interactions), Plaid (Banking API).

## Key Features
*   **Automated Tracking:** Daily fetch of new transactions via Plaid API.
*   **Discord Integration:** Interactive buttons and menus for classification directly in Discord.
    *   **Shared:** 50/50 split or custom percentage (e.g., "You pay 30%").
    *   **Individual:** Assign full amount to User A or User B.
    *   **Custom:** Enter specific dollar amount for split.
    *   **Ignore:** Exclude transaction from all calculations.
    *   **Notes:** Add context to transactions via modal input.
*   **Settlement Calculation:** Automated monthly report (1st of month) covering the billing cycle (previous month 10th to current month 9th).
*   **Database:** Uses DynamoDB for atomic, scalable storage (replaced CSV/S3).

## Architecture & Data Flow
1.  **Daily Scan (Cron):** 
    *   Triggered daily at 9 AM UTC.
    *   Fetches recent transactions from Plaid.
    *   Writes new transactions to DynamoDB (atomic batch write).
    *   Sends notification to Discord Classifications Channel with interactive components.
2.  **User Interaction (Webhook):**
    *   User clicks button/menu in Discord.
    *   Discord sends POST request to API Gateway (`/discord`).
    *   **Webhook Lambda:** Verifies Ed25519 signature, updates transaction in DynamoDB (atomic update), and updates the Discord message with the new status (e.g., green embed for classified, grey for ignored).
3.  **Monthly Settlement (Cron):**
    *   Triggered monthly on the 1st at 10 AM UTC.
    *   Queries DynamoDB (using Date Index) for the billing cycle.
    *   Calculates totals for User A and User B based on classifications.
    *   Ignores transactions marked as "excluded".
    *   Posts summary to Discord Settlements Channel.

## Development Conventions

### Tech Stack & Tools
*   **Runtime:** Python 3.11+
*   **Infrastructure:** AWS SAM (`template.yaml`)
*   **Dependencies:** `requirements.txt` (includes `boto3`, `plaid-python`, `pynacl`, `requests`).
*   **Testing:** `pytest` using `pytest-mock` and `moto` (DynamoDB mock).
*   **Linting/Formatting:** Standard Python tooling.

### Project Structure
*   `lambdas/`: AWS Lambda function handlers.
    *   `daily_scan.py`: Fetches Plaid data and triggers settlement.
    *   `webhook.py`: Handles Discord interactions (buttons, menus, modals).
*   `lib/`: Core business logic and clients.
    *   `plaid_client.py`: Plaid API interaction.
    *   `discord_client.py`: Discord API interaction (messages, components, signature verification).
    *   `storage.py`: DynamoDB CRUD operations.
    *   `settlement.py`: Logic for calculating user totals.
*   `tests/`: Unit and integration tests.
*   `config.py`: Environment variable management.
*   `template.yaml`: AWS SAM infrastructure definition.

### Building & Running
*   **Install Dependencies:** `pip install -r requirements.txt`
*   **Test:** `pytest` (or `.venv/bin/pytest`)
    *   *Note:* Tests use a custom S3 mock; no AWS credentials required for unit tests.
*   **Build:** `sam build`
*   **Deploy:** `sam deploy --guided` (first time), `sam deploy` (subsequent)

### Environment Variables
Local development requires a `.env` file (see `.env.example`). Key variables:
*   `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY`: From Discord Developer Portal.
*   `PLAID_CLIENT_ID`, `PLAID_SECRET`: From Plaid Dashboard.
*   `S3_BUCKET`: Name of the S3 bucket for storage.
*   `USER_A_NAME`, `USER_B_NAME`: Display names for users.

## Recent Changes
*   **DynamoDB Migration:** Replaced S3/CSV storage with DynamoDB to fix concurrency issues and improve scalability.
*   **Ignore Feature:** Added "Ignore" button to transaction notifications. Excluded transactions are skipped in settlement calculations.
*   **Refactoring:** Migrated from SMS (Twilio) to Discord Interactions.
