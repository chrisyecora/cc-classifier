# Production Roadmap: CC-Classifier

This document outlines the transition of the Credit Card Tracker from a "hobbyist script" to an **enterprise-grade production system**. This roadmap serves as a guide for development and as a portfolio piece to demonstrate mastery of the Software Development Lifecycle (SDLC).

## Phase 1: Foundation & CI/CD (Current Focus)
**Goal:** Automate deployments and ensure code quality before it reaches AWS.
- [x] **GitHub Actions Integration:** 
    - Build and test on Pull Requests.
    - Automatic `sam build` and `sam deploy` on merge to `main`.
- [x] **Linting & Formatting:** Integrate `ruff` or `black/flake8` into the pipeline.
- [x] **Unit Test Enforcement:** Ensure `pytest` passes before any deployment.

## Phase 2: Multi-Environment & Security
**Goal:** Separate "experimentation" from "production" data and secure credentials.
- [x] **Bifurcated Stacks:** Use SAM parameters to maintain separate `dev` and `prod` stacks (different DynamoDB tables, different Discord channels).
- [x] **Secret Management:** Move from `.env` files to **AWS Systems Manager (SSM) Parameter Store** or **Secrets Manager**.
- [x] **IAM Least Privilege:** Audit Lambda execution roles to ensure they only have access to specific resources.

## Phase 3: Observability & Reliability
**Goal:** Know when things break before the users (you and your partner) do.
- [ ] **Structured Logging:** Implement JSON logging for easier querying in CloudWatch.
- [ ] **CloudWatch Alarms:** Set up alerts for Lambda failures or Plaid connection errors.
- [ ] **Dead Letter Queues (DLQ):** Handle failed notification attempts or webhook processing errors gracefully.

## Phase 4: Data Visualization (The Dashboard)
**Goal:** Move beyond the Discord UI for deep historical insights.
- [ ] **Next.js Web App:** Create a lightweight dashboard for monthly spending trends.
- [ ] **API Gateway Integration:** Add a specific `/stats` or `/history` endpoint to the SAM template for the frontend to consume.
- [ ] **Visual Components:** Use libraries like `Tremor` or `Recharts` for interactive spending charts.

## Phase 5: Intelligent Insights (LLM Integration)
**Goal:** Add conversational flexibility and sophisticated data synthesis.
- [ ] **AWS Bedrock Integration:** Link the bot to Claude 3 Haiku.
- [ ] **Natural Language Queries:** Support `/ask` commands ("How much was our electricity bill over the last 3 months?").
- [ ] **Subscription Watchdog:** Use standard logic + LLM to detect and warn about price hikes in recurring services.

---

## Technical Debt & Maintenance
- [ ] Migrate any remaining hardcoded logic to configuration files.
- [ ] Enhance test coverage for the `webhook` interaction logic.
- [ ] Document the data schema for the `Transactions` table to ensure consistency.
