# Statement review app

The admin app is a Vite/React/TypeScript build in `web/`. Its static files are served by CloudFront from a private S3 bucket. CloudFront forwards `/api/*` to the authenticated API Gateway REST API. The page never receives AWS credentials or the Cognito password.

## Monthly workflow

1. The scheduled job posts a reminder in the settlements Discord channel on the 1st. It does not publish a settlement amount.
2. Open the admin site and sign in through Cognito. Select the statement ending month.
3. Confirm the inclusive start and end dates against the card statement. A new draft starts the day after the previous confirmed statement; its suggested end is the 9th.
4. Correct classifications, splits, ignored status, and notes. The totals are calculated by the Python settlement logic and updated after each save.
5. When every transaction is classified or ignored, publish the settlement. Later changes are marked unpublished until a revision is posted.

Statement metadata and the last published summary are stored under partition key `STATEMENT` in the existing DynamoDB table. Transactions remain live under `TRX`. The 2026-09 statement can be confirmed as 2026-08-12 through 2026-09-09. Adjacent confirmed months must join without a gap or overlap.

## Shared admin account

SAM creates a Cognito user pool with public sign-up disabled and a password policy requiring at least 16 characters, upper and lower case letters, a number, and a symbol. It does **not** create or store a password. After deploying the stack, create the single account in the AWS console (Cognito → user pool → Create user), supply an email address, and have the account owner set its permanent strong password on first login. The pool ID is the `AdminUserPoolId` stack output. Password resets use that email address.

The React app redirects to Cognito managed login using an authorization code and PKCE. API Gateway's Cognito authorizer validates the token on every `/api/*` request. The app client has no secret and public sign-up is disabled. Sharing this account means actions cannot be attributed separately to Chris or Caro.

## Build and deploy

Production CI runs the Python tests and frontend build, deploys SAM, generates `web/dist/config.json` from stack outputs, then uploads the static build. `config.json` contains only public Cognito IDs, the domain, and the site URL. The deployment helper is `scripts/deploy_admin_site.py`.

The PR workflow runs tests and the frontend build, then deploys passing same-repository PRs to the shared `credit-card-tracker-dev` stack in the same AWS account as production. It reuses the existing GitHub AWS credentials and the existing `cc-classifier/prod/secrets` secret. Schedules are disabled, and the dev stack has its own DynamoDB table, Cognito pool, API, and site. Its URL appears in the GitHub Actions job summary. Fork PRs run checks but cannot deploy because GitHub does not provide secrets to them. The dev stack persists between PRs, so its Cognito account and test transactions remain available; the most recently deployed PR owns the preview.

No additional AWS credentials, Discord channels, or Discord secrets are needed for the preview. Every outgoing Discord message from `Environment=dev` starts with **DEV TESTING**. Dev messages omit interactive components because Discord sends button clicks for this bot to its single configured webhook, which points at production. Create the shared admin user once in the dev Cognito pool after its first deployment. Using the production AWS deployment credentials in a same-repository PR means anyone able to push such a PR can execute code with those credentials; restrict write access to this repository accordingly.

For a manual dev deployment, deploy `template.yaml` with SAM using `Environment=dev`, `EnableSchedules=false`, and `SecretsEnvironment=prod`, plus the existing required Discord/Plaid/user parameters. Then run `npm ci --prefix web`, `npm run build --prefix web`, and `.venv/bin/python scripts/deploy_admin_site.py --stack-name credit-card-tracker-dev`.

The local Vite build can be checked with `npm run build --prefix web`. Browser sign-in uses the deployed CloudFront callback URL, so an end-to-end browser test should use the dev site rather than the local Vite server.
