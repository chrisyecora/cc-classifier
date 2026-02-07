# Setup Guide: Credit Card Tracker

This guide outlines the accounts you need to create, the API keys you need to gather, and the steps to deploy the application.

## 1. AWS Account (Infrastructure)

The application runs on AWS (Lambda, S3, EventBridge, API Gateway).

1.  **Create an Account:** [aws.amazon.com](https://aws.amazon.com/)
2.  **Install AWS CLI:** [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
3.  **Configure CLI:** Run `aws configure` in your terminal. You will need your AWS Access Key ID and Secret Access Key (create these in IAM console).
4.  **Install SAM CLI:** `brew install aws-sam-cli` (already done).

## 2. Plaid Account (Bank Transactions)

Plaid connects to your credit card account to fetch transactions.

1.  **Create an Account:** [dashboard.plaid.com](https://dashboard.plaid.com/signup)
2.  **Get API Keys:** Go to **Team Settings > Keys**.
    *   `PLAID_CLIENT_ID`
    *   `PLAID_SECRET` (Use the "Sandbox" secret for testing, or "Development"/"Production" for real use).
3.  **Generate Access Token**:
    *   For **Sandbox** (Fake data): You can generate a token via API.
    *   For **Real Accounts** (Development/Production): You must use the [Plaid Quickstart](https://github.com/plaid/quickstart) to run a local server, login to your bank via Plaid Link, and get the `access_token`.

    **Quick Sandbox Token (for testing):**
    Run these commands in your terminal (replace `YOUR_CLIENT_ID` and `YOUR_SECRET`):

    ```bash
    # 1. Create a public token for a fake institution
    curl -X POST https://sandbox.plaid.com/sandbox/public_token/create \
      -H 'Content-Type: application/json' \
      -d '{"client_id": "YOUR_CLIENT_ID", "secret": "YOUR_SECRET", "institution_id": "ins_109508", "initial_products": ["transactions"]}'
    
    # Response: { "public_token": "public-sandbox-..." }

    # 2. Exchange public token for access token
    curl -X POST https://sandbox.plaid.com/item/public_token/exchange \
      -H 'Content-Type: application/json' \
      -d '{"client_id": "YOUR_CLIENT_ID", "secret": "YOUR_SECRET", "public_token": "PASTE_PUBLIC_TOKEN_HERE"}'

    # Response: { "access_token": "access-sandbox-..." }
    ```
    *   **Save this `access_token`**. This is your `PlaidAccessToken`.

## 3. Twilio Account (SMS)

Twilio handles sending and receiving SMS messages.

1.  **Create an Account:** [twilio.com](https://www.twilio.com/)
2.  **Get Credentials:** Go to the Console Dashboard.
    *   `TWILIO_ACCOUNT_SID`
    *   `TWILIO_AUTH_TOKEN`
3.  **Get a Phone Number:**
    *   Buy a phone number (usually ~$1.15/mo).
    *   Make sure it has **SMS** capabilities.
    *   **Save this number** (E.164 format, e.g., `+15551234567`). This is your `TwilioPhoneNumber`.

## 4. Deployment

Once you have all the keys, deploy the application.

1.  **Build:**
    ```bash
    sam build
    ```

2.  **Deploy:**
    ```bash
    sam deploy --guided
    ```
    
    You will be prompted to enter the values you gathered above:

    *   **Stack Name**: `cc-classifier` (or any name)
    *   **AWS Region**: `us-east-1` (or your preferred region)
    *   **Parameter Environment**: `dev` (use `prod` for real money)
    *   **Parameter TwilioAccountSid**: (Paste your SID)
    *   **Parameter TwilioAuthToken**: (Paste your Token)
    *   **Parameter TwilioPhoneNumber**: (Paste your Twilio Number, e.g., `+1555...`)
    *   **Parameter PlaidClientId**: (Paste your Plaid Client ID)
    *   **Parameter PlaidSecret**: (Paste your Plaid Secret)
    *   **Parameter PlaidAccessToken**: (Paste the Access Token you generated)
    *   **Parameter UserAName**: (e.g., `Alex`)
    *   **Parameter UserAPhone**: (Your phone number, e.g., `+1555...`)
    *   **Parameter UserBName**: (e.g., `Beth`)
    *   **Parameter UserBPhone**: (Partner's phone number, e.g., `+1555...`)
    *   **Confirm changes before deploy**: `y`
    *   **Allow SAM CLI IAM role creation**: `y`
    *   **Save arguments to configuration file**: `y`

## 5. Post-Deployment: Connect Webhook

After deployment finishes, SAM will output a **WebhookUrl**. You need to tell Twilio to send incoming SMS to this URL.

1.  **Copy the WebhookUrl** from the deployment output (e.g., `https://xyz.execute-api.us-east-1.amazonaws.com/Prod/sms`).
2.  Go to **Twilio Console > Phone Numbers > Manage > Active Numbers**.
3.  Click on your phone number.
4.  Scroll down to **Messaging**.
5.  Under **A MESSAGE COMES IN**:
    *   Select **Webhook**.
    *   Paste your **WebhookUrl**.
    *   Ensure method is **POST**.
6.  Click **Save**.

## 6. Testing It Out

1.  **Manual Trigger:** You can manually trigger the daily scan via AWS Console (Lambda > `daily-scan` > Test) to fetch transactions immediately.
2.  **Receive SMS:** If new transactions are found, both users will get an SMS.
3.  **Reply:** Reply with `1S` or `1A` to classify.
4.  **Confirmation:** You should get a confirmation SMS back.
