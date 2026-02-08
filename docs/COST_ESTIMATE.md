# Estimated Monthly Operating Costs

This document provides a cost breakdown for running the Credit Card Tracker in a "serverless" AWS environment.

## Summary

| Service | Estimated Monthly Cost | Notes |
| :--- | :--- | :--- |
| **Plaid** | **$0.30 - $0.30** | $0.30 per connected active account/month. (Assuming 1 account). |
| **Discord** | **$0.00** | Free API usage for bots. |
| **AWS Lambda** | **$0.00** | Free Tier covers 400,000 GB-seconds/month (Way more than needed). |
| **AWS API Gateway** | **$0.00** | Free Tier covers 1 million requests/month. |
| **AWS S3** | **$0.01 - $0.05** | Storage is negligible (< 1MB). Costs are mostly for PUT/GET requests (Standard class). |
| **AWS EventBridge** | **$0.00** | Free Tier covers schema registry and events. |
| **Total** | **~$0.35 / month** | Essentially just the Plaid connection fee + tiny S3 usage. |

---

## Detailed Breakdown

### 1. Plaid (Banking API)
*   **Cost:** $0.30 / account / month.
*   **Usage:** If you connect 1 credit card account (an "Item"), Plaid charges $0.30/month for the Transactions product on the Production plan.
*   **Plan:** "Production" (Launch/Pay-as-you-go). No monthly minimums for the first $100 spent.

### 2. AWS Lambda (Compute)
*   **Cost:** $0.20 per 1M requests + $0.0000166667 per GB-second.
*   **Free Tier:** 1 Million requests & 400,000 GB-seconds per month.
*   **Usage:**
    *   **Daily Scan:** Runs 1 time/day * 30 days = 30 invocations.
    *   **Webhooks:** Assuming 50 transactions/month = 50 invocations.
    *   **Total:** ~80 invocations/month.
*   **Verdict:** **Free.** You are using < 0.01% of the Free Tier.

### 3. AWS API Gateway (HTTP Endpoint)
*   **Cost:** $1.00 per million requests.
*   **Free Tier:** 1 million requests per month (for 12 months).
*   **Usage:** 50 transactions/month = 50 webhook calls from Discord.
*   **Verdict:** **Free.** Even after 12 months, the cost is fractions of a penny ($0.00005).

### 4. AWS S3 (Storage)
*   **Cost:** $0.023 per GB (Standard). $0.005 per 1,000 PUT requests. $0.0004 per 1,000 GET requests.
*   **Usage:**
    *   **Storage:** The CSV file is tiny (KB). Cost is negligible.
    *   **Requests:**
        *   Daily Scan: 1 GET + 1 PUT (if new txns).
        *   Webhooks: 1 GET + 1 PUT per classification.
        *   Total Requests: ~150-200 per month.
*   **Verdict:** **< $0.01.** Maybe a few cents if you heavily test.

### 5. Discord (Notifications)
*   **Cost:** Free.
*   **Usage:** Creating Applications and Bots is free. Message limits are generous (50/sec), far above your needs.

---

## Usage Scalability
Even if you process **1,000 transactions a month**, the AWS cost would likely stay under **$0.10**. The primary cost driver is Plaid, which scales linearly with the number of bank accounts you connect ($0.30 each).
