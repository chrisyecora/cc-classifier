# Credit Card Tracker (cc-classifier)

A serverless Discord bot that automates credit card expense tracking and splitting for two users. It fetches transactions via Plaid, allows interactive classification in Discord, and calculates monthly settlements.

## 🚀 Features

*   **Automated Tracking**: Daily scan (9 AM UTC) fetches new transactions from Plaid.
*   **Discord Integration**:
    *   **Interactive UI**: Classify transactions using Buttons and Dropdown Menus.
    *   **Splitting Options**:
        *   **Individual**: Assign 100% to User A or User B.
        *   **Shared**: Split 50/50 or custom percentages (e.g., "You pay 30%").
        *   **Custom Amount**: Enter a specific dollar amount for the split.
    *   **Context**: Add **Notes** to any transaction via a modal.
    *   **Management**: **Ignore** transactions (exclude from totals) or **Undo** a classification.
*   **Monthly Settlements**: Automatically calculates who owes what on the 1st of every month (covering the previous billing cycle).
*   **Serverless Architecture**: Built on AWS Lambda & DynamoDB for low cost and high availability.

## 🏗️ Architecture

The project is built using **AWS SAM (Serverless Application Model)** and Python 3.11.

*   **AWS Lambda**:
    *   `DailyScanFunction`: Triggered by EventBridge (Cron). Fetches data from Plaid, updates DynamoDB, and sends Discord notifications.
    *   `WebhookFunction`: Handles Discord interactions (API Gateway HTTP POST). Verifies signatures and updates transaction state.
*   **Amazon DynamoDB**: Stores all transaction data with atomic updates. Replaced the legacy CSV/S3 storage.
*   **Amazon EventBridge**: Schedules the daily scan and monthly settlement reports.
*   **API Gateway**: Exposes the public endpoint for Discord Webhooks.

### Project Structure

```
.
├── lambdas/           # Lambda function handlers
│   ├── daily_scan.py  # Cron job for fetching data & reporting
│   └── webhook.py     # Discord interaction handler
├── lib/               # Core business logic
│   ├── discord_client.py
│   ├── plaid_client.py
│   ├── settlement.py
│   └── storage.py     # DynamoDB operations
├── tests/             # Pytest suite
├── template.yaml      # AWS SAM Infrastructure-as-Code
└── requirements.txt   # Python dependencies
```

## 🛠️ Setup & Deployment

### Prerequisites

*   **AWS CLI** & **AWS SAM CLI** installed and configured.
*   **Python 3.11+**
*   **Discord Bot Application**: Created in the [Discord Developer Portal](https://discord.com/developers/applications).
*   **Plaid Account**: Client ID and Secret from the [Plaid Dashboard](https://dashboard.plaid.com/).

### Environment Variables

You will need the following credentials:

*   `DISCORD_BOT_TOKEN`, `DISCORD_PUBLIC_KEY`
*   `PLAID_CLIENT_ID`, `PLAID_SECRET`
*   `PLAID_ENV` (sandbox, development, or production)
*   `USER_A_NAME`, `USER_B_NAME` (Display names)

### Local Development

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/cc-classifier.git
    cd cc-classifier
    ```

2.  **Install dependencies**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run Tests**:
    The project uses `pytest` with `moto` to mock AWS services locally.
    ```bash
    pytest
    ```

### Deployment

1.  **Build the application**:
    ```bash
    sam build
    ```

2.  **Deploy to AWS**:
    ```bash
    sam deploy --guided
    ```
    Follow the prompts to input your Discord and Plaid credentials.

3.  **Configure Discord**:
    *   Copy the `InteractionsEndpointUrl` output from the deployment.
    *   Paste it into the **Interactions Endpoint URL** field in your Discord App settings.

## 🎮 Usage

1.  **New Transactions**: appear in the configured `DiscordClassificationsChannel`.
2.  **Classify**:
    *   Click **User A** or **User B** to assign the full amount.
    *   Click **Shared** to split 50/50.
    *   Use the **Dropdown Menu** for custom percentage splits.
    *   Click **Ignore** to exclude a transaction (e.g., payments).
    *   Click **Note** to add a text note.
3.  **Settlement**:
    *   On the 1st of the month, a summary report is posted to the `DiscordSettlementsChannel`.

## 📄 License

[MIT](LICENSE)
