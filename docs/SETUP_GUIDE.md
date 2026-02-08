# Setup Guide: Credit Card Tracker (Discord Edition)

This guide outlines the accounts you need to create, the API keys you need to gather, and the steps to deploy the application.

## 1. AWS Account (Infrastructure)
1.  **Create an Account:** [aws.amazon.com](https://aws.amazon.com/)
2.  **Install AWS CLI:** `brew install awscli` and run `aws configure`.
3.  **Install SAM CLI:** `brew install aws-sam-cli`.

## 2. Plaid Account (Bank Transactions)
1.  **Create Account:** [dashboard.plaid.com](https://dashboard.plaid.com/signup)
2.  **Get Keys:** Team Settings > Keys (`Client ID`, `Secret`).
3.  **Get Access Token:** Use the [Plaid Quickstart](https://github.com/plaid/quickstart) to link your real bank account and generate an `access_token`.

## 3. Discord Account & Bot
1.  **Developer Portal:** [discord.com/developers/applications](https://discord.com/developers/applications)
2.  **Create Application:** Name it "CreditCardTracker".
3.  **Bot:** 
    *   Click "Bot" > "Reset Token". Copy the **Token** (`DISCORD_BOT_TOKEN`).
    *   Enable "Message Content Intent" (optional but good practice).
4.  **General Info:**
    *   Copy **Application ID**.
    *   Copy **Public Key** (`DISCORD_PUBLIC_KEY`).
5.  **Invite to Server:**
    *   OAuth2 > URL Generator > check `bot` and `applications.commands`.
    *   Bot Permissions > check `Send Messages`, `Read Messages`, `Embed Links`.
    *   Open URL and invite to your server.
6.  **Get Channel ID:**
    *   Enable Developer Mode in Discord App Settings.
    *   Right-click your desired channel > Copy ID (`DISCORD_CHANNEL_ID`).

## 4. Deployment
1.  **Build:**
    ```bash
    sam build
    ```
2.  **Deploy:**
    ```bash
    sam deploy --guided
    ```
    Enter your keys when prompted.
    *   **PlaidEnv**: `development` (for real data) or `sandbox` (fake).

## 5. Post-Deployment: Connect Interactions Endpoint
1.  Copy the **InteractionsEndpointUrl** output from the SAM deploy (e.g., `https://.../discord`).
2.  Go back to **Discord Developer Portal** > **General Information**.
3.  Paste the URL into **"Interactions Endpoint URL"**.
4.  Click **"Save Changes"**.
    *   *Note: Discord will immediately hit your endpoint to verify the signature. If your Lambda isn't working or keys are wrong, this will fail.*

## 6. Testing
1.  **Local Test:**
    *   Configure `.env`.
    *   Run `python scripts/run_local.py scan`.
2.  **Discord Test:**
    *   If the scan finds transactions, a message with buttons will appear in Discord.
    *   Click a button. It should update to "✅ Classified as ...".