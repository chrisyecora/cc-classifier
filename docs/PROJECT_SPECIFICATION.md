# Credit Card Tracker - Complete Project Specification

**Purpose**: SMS-based credit card expense tracker for 2 people sharing a card. Automatically fetches transactions daily, allows classification via SMS, and calculates monthly settlement.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [File Structure](#file-structure)
5. [Configuration](#configuration)
6. [Data Schemas](#data-schemas)
7. [SMS Protocol](#sms-protocol)
8. [Implementation Details](#implementation-details)
9. [Testing Requirements](#testing-requirements)
10. [Deployment](#deployment)
11. [Setup Prerequisites](#setup-prerequisites)

---

## Overview

### Problem Statement
Two people share a credit card. At month-end, they need to know how much each person owes based on their individual spending vs shared expenses.

### Solution
- Daily Lambda fetches new transactions from Plaid API
- SMS sent to both users listing unclassified transactions
- Users reply via SMS to classify: Shared (S), Alex's (A), or Beth's (B)
- First valid reply wins; other user is notified
- Monthly settlement calculates each person's total owed

### Key Features
- Automatic daily transaction fetching
- SMS-based classification (no app install required)
- Custom split percentages for shared expenses (e.g., "1S70" = I pay 70%)
- Monthly settlement calculation based on billing cycle (10th-9th)
- First-reply-wins conflict resolution

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Plaid     │────▶│   Lambda    │────▶│   Twilio    │
│   (daily)   │     │ daily_scan  │     │   (SMS)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │                   │
                   ┌──────▼──────┐            │
                   │  S3 (CSV)   │            ▼
                   └─────────────┘       Users (SMS)
                          ▲                   │
                          │                   │
                   ┌──────┴──────┐            │
                   │   Lambda    │◀───────────┘
                   │   webhook   │  API Gateway
                   └─────────────┘
```

### Flow
1. **Daily (9 AM UTC)**: EventBridge triggers `daily_scan` Lambda
2. Lambda fetches transactions from Plaid, appends to S3 CSV
3. If unclassified transactions exist, SMS sent to both users
4. User replies with classification (e.g., "1S\n2A")
5. Twilio webhook → API Gateway → `webhook` Lambda
6. Lambda parses reply, updates CSV, notifies other user
7. **Monthly (1st, 10 AM UTC)**: Settlement calculated and SMS sent

---

## Technology Stack

- **Runtime**: Python 3.11
- **Infrastructure**: AWS (Lambda, S3, API Gateway, EventBridge)
- **IaC**: AWS SAM (template.yaml)
- **SMS**: Twilio
- **Banking**: Plaid API
- **Storage**: CSV files in S3
- **Testing**: pytest with mocks (no moto - use in-memory S3 mock)

---

## File Structure

```
/
├── lambdas/
│   ├── daily_scan.py      # EventBridge trigger: fetch Plaid, send SMS, monthly settlement
│   └── webhook.py         # API Gateway trigger: process SMS replies
├── lib/
│   ├── __init__.py
│   ├── plaid_client.py    # Plaid API wrapper with retry logic
│   ├── twilio_client.py   # Twilio SMS send/receive
│   ├── storage.py         # S3 CSV read/write operations
│   ├── parser.py          # SMS reply parsing
│   └── settlement.py      # Monthly settlement calculation
├── tests/
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures (in-memory S3 mock)
│   ├── test_storage.py
│   ├── test_plaid_client.py
│   ├── test_twilio_client.py
│   ├── test_parser.py
│   ├── test_webhook.py
│   ├── test_settlement.py
│   └── test_daily_scan.py
├── config.py              # Environment variable management
├── requirements.txt
├── pytest.ini
└── template.yaml          # SAM template
```

---

## Configuration

### Environment Variables (set via SAM template parameters)

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT` | `dev` or `prod` |
| `S3_BUCKET` | Bucket name for CSV storage |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Twilio phone number (E.164) |
| `PLAID_CLIENT_ID` | Plaid Client ID |
| `PLAID_SECRET` | Plaid Secret |
| `PLAID_ACCESS_TOKEN` | Plaid Access Token |
| `USER_A_NAME` | First user name (default: Alex) |
| `USER_A_PHONE` | First user phone (E.164) |
| `USER_B_NAME` | Second user name (default: Beth) |
| `USER_B_PHONE` | Second user phone (E.164) |

### config.py

```python
"""Configuration management from environment variables."""
import os
from dataclasses import dataclass

@dataclass
class Config:
    environment: str
    s3_bucket: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    plaid_client_id: str
    plaid_secret: str
    plaid_access_token: str
    user_a_name: str
    user_a_phone: str
    user_b_name: str
    user_b_phone: str

_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config(
            environment=os.environ.get("ENVIRONMENT", "dev"),
            s3_bucket=os.environ["S3_BUCKET"],
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
            plaid_client_id=os.environ["PLAID_CLIENT_ID"],
            plaid_secret=os.environ["PLAID_SECRET"],
            plaid_access_token=os.environ["PLAID_ACCESS_TOKEN"],
            user_a_name=os.environ.get("USER_A_NAME", "Alex"),
            user_a_phone=os.environ["USER_A_PHONE"],
            user_b_name=os.environ.get("USER_B_NAME", "Beth"),
            user_b_phone=os.environ["USER_B_PHONE"],
        )
    return _config

def reset_config() -> None:
    global _config
    _config = None
```

---

## Data Schemas

### transactions.csv

```csv
transaction_id,date,amount,merchant,classification,classified_by,percentage,notified_at
plaid_abc123,2026-01-28,543.25,COSTCO,S,Alex,70,2026-01-28T10:30:00Z
plaid_def456,2026-01-28,7.52,Chewy,A,Alex,,2026-01-28T10:30:00Z
plaid_ghi789,2026-01-28,125.00,Target,,,
```

| Field | Description |
|-------|-------------|
| `transaction_id` | Plaid transaction ID (unique) |
| `date` | Transaction date (YYYY-MM-DD) |
| `amount` | Transaction amount (positive decimal, string) |
| `merchant` | Merchant name from Plaid |
| `classification` | S (shared), A (user A), B (user B), or empty |
| `classified_by` | Name of user who classified |
| `percentage` | Classifier's share for shared (empty = 50%) |
| `notified_at` | ISO timestamp when classification SMS sent |

---

## SMS Protocol

### Outbound (Daily Transaction List)

```
2026-01-28 Transactions:
1. COSTCO $543.25
2. Chewy $7.52

Reply format: #S #A #B
S=shared, A=Alex, B=Beth
For custom split: #S70 (you pay 70%)
```

### Inbound (User Reply)

Newline-delimited classification codes:
```
1S
2A
3S70
```

**Parsing Rules:**
- Split on newlines, trim whitespace
- Regex per line: `^(\d+)([SABsab])(\d+)?$`
- Case-insensitive
- Skip blank lines
- Invalid lines: skip and continue

**Percentage Semantics:**
- `1S70` by Alex → Alex pays 70%, Beth pays 30%
- `1S70` by Beth → Beth pays 70%, Alex pays 30%
- `1S` (no percentage) → 50/50

### Confirmation Messages

To classifier: `"✓ #1: COSTCO → Shared (you: 70%)"`

To other user: `"Alex classified: COSTCO $543.25 → Shared (Alex: 70%, you: 30%)"`

---

## Implementation Details

### lib/storage.py

Key functions:
- `read_transactions()` → `list[dict]`: Read CSV from S3
- `write_transactions(transactions)`: Write CSV to S3
- `append_transactions(new_transactions)` → `int`: Append, skip duplicates, return added count
- `update_transaction(transaction_id, classification, classified_by, percentage)` → `bool`: Update if not already classified
- `get_unclassified_transactions()` → `list[dict]`: Filter unclassified
- `get_statement_period(settlement_date)` → `tuple[date, date]`: Calculate billing cycle dates
- `get_transactions_for_statement_period(settlement_date)` → `list[dict]`: Filter by billing cycle
- `read_users()` → `dict[str, dict]`: Get users from config
- `get_user_by_phone(phone)` → `dict | None`: Find user by phone
- `get_other_user(user_id)` → `dict`: Get the other user

**Statement Period Logic (Critical):**
- Billing cycle: 10th of month to 9th of next month
- Settlement on Feb 1st covers: Dec 10 - Jan 9 (January statement)
- Transaction on Jan 10th belongs to February statement

### lib/plaid_client.py

Key functions:
- `get_plaid_client()`: Create Plaid API client (sandbox for dev, production for prod)
- `fetch_transactions(start_date, end_date, max_retries=3)` → `list[dict]`: Fetch with exponential backoff retry
- `_transform_transactions(plaid_transactions)` → `list[dict]`: Convert to storage format, filter out credits

### lib/twilio_client.py

Key functions:
- `send_sms(to, body, retry=True)` → `bool`: Send SMS with one retry on failure
- `format_transaction_list(transactions)` → `str`: Format for outbound SMS
- `send_transaction_notification(transactions, users)` → `bool`: Send to both users
- `send_classification_confirmation(transaction, classifier, classification, percentage)` → `bool`
- `send_classification_notification(transaction, classifier, other_user, classification, percentage)` → `bool`

### lib/parser.py

```python
@dataclass
class Classification:
    transaction_number: int  # 1-indexed
    classification: str      # S, A, or B
    percentage: int | None   # Classifier's percentage (None = 50%)

@dataclass
class ParseResult:
    classifications: list[Classification]
    errors: list[str]  # Invalid lines

def parse_reply(message: str) -> ParseResult: ...
def parse_line(line: str) -> Classification | None: ...
def format_error_response(errors: list[str]) -> str: ...
def format_invalid_transaction_response(number: int, max_number: int) -> str: ...
```

### lib/settlement.py

```python
@dataclass
class UserSettlement:
    user_id: str
    user_name: str
    total_owed: Decimal
    transaction_count: int

@dataclass
class SettlementResult:
    statement_start: date
    statement_end: date
    user_a: UserSettlement
    user_b: UserSettlement
    unclassified_count: int

def calculate_settlement(settlement_date: date) -> SettlementResult: ...
def format_settlement_sms(result: SettlementResult) -> str: ...
```

**Settlement Logic:**
- Individual (A or B): 100% to that user
- Shared without %: 50/50
- Shared with %: Classifier pays their %, other pays remainder

### lambdas/daily_scan.py

Handler routes based on EventBridge rule:
- Daily schedule → `_handle_daily_scan()`: Fetch Plaid, append S3, send SMS
- Monthly schedule → `_handle_monthly_settlement()`: Calculate settlement, send SMS

Detection: Check if `"MonthlySettlement"` in event resources ARN.

### lambdas/webhook.py

1. Parse Twilio POST body (URL-encoded: `From`, `Body`)
2. Identify user by phone
3. Get unclassified transactions
4. Parse reply with `parse_reply()`
5. For each valid classification:
   - Validate transaction number exists
   - Call `update_transaction()`
   - If updated, notify other user
6. Return TwiML XML response with confirmation message

---

## Testing Requirements

### Test Structure

Use pytest with in-memory S3 mock (avoid moto due to Python compatibility issues).

**conftest.py fixtures:**
- `env_setup`: Set all environment variables, reset config before/after each test
- `s3_mock`: In-memory S3 mock that patches `get_s3_client()`
- `sample_transactions`: 2 unclassified transactions
- `classified_transactions`: 2 classified transactions

**In-Memory S3 Mock:**
```python
class InMemoryS3:
    def __init__(self):
        self.storage: dict[str, dict[str, str]] = {}
        self.exceptions = type("Exceptions", (), {
            "NoSuchKey": type("NoSuchKey", (Exception,), {})
        })()

    def get_object(self, Bucket: str, Key: str) -> dict: ...
    def put_object(self, Bucket: str, Key: str, Body: str | bytes, ContentType: str = None) -> dict: ...
```

### Test Coverage

Target: 115+ tests covering all specs.

| Test File | Coverage |
|-----------|----------|
| test_storage.py | CSV operations, statement period logic |
| test_plaid_client.py | Plaid fetch, retry logic, transform |
| test_twilio_client.py | SMS send, format, retry |
| test_parser.py | Parse reply, edge cases |
| test_webhook.py | Full webhook flow |
| test_settlement.py | Settlement calculation |
| test_daily_scan.py | Lambda handler routing |

---

## Deployment

### requirements.txt

```
boto3>=1.34.0
twilio>=8.10.0
plaid-python>=15.0.0

# Testing
pytest>=8.0.0
pytest-mock>=3.12.0
```

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

### template.yaml (SAM)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Credit Card Tracker - SMS-based expense classification

Parameters:
  Environment:
    Type: String
    Default: dev
    AllowedValues: [dev, prod]
  TwilioAccountSid:
    Type: String
    NoEcho: true
  TwilioAuthToken:
    Type: String
    NoEcho: true
  TwilioPhoneNumber:
    Type: String
  PlaidClientId:
    Type: String
    NoEcho: true
  PlaidSecret:
    Type: String
    NoEcho: true
  PlaidAccessToken:
    Type: String
    NoEcho: true
  UserAName:
    Type: String
    Default: Alex
  UserAPhone:
    Type: String
  UserBName:
    Type: String
    Default: Beth
  UserBPhone:
    Type: String

Globals:
  Function:
    Runtime: python3.11
    Timeout: 30
    MemorySize: 256
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        S3_BUCKET: !Ref TransactionsBucket
        TWILIO_ACCOUNT_SID: !Ref TwilioAccountSid
        TWILIO_AUTH_TOKEN: !Ref TwilioAuthToken
        TWILIO_PHONE_NUMBER: !Ref TwilioPhoneNumber
        PLAID_CLIENT_ID: !Ref PlaidClientId
        PLAID_SECRET: !Ref PlaidSecret
        PLAID_ACCESS_TOKEN: !Ref PlaidAccessToken
        USER_A_NAME: !Ref UserAName
        USER_A_PHONE: !Ref UserAPhone
        USER_B_NAME: !Ref UserBName
        USER_B_PHONE: !Ref UserBPhone

Resources:
  TransactionsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub credit-card-tracker-${Environment}-${AWS::AccountId}
      PublicAccessBlockConfiguration:
        BlockPublicAcls: true
        BlockPublicPolicy: true
        IgnorePublicAcls: true
        RestrictPublicBuckets: true

  DailyScanFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub credit-card-tracker-daily-scan-${Environment}
      Handler: daily_scan.handler
      CodeUri: lambdas/
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref TransactionsBucket
      Events:
        DailySchedule:
          Type: Schedule
          Properties:
            Schedule: cron(0 9 * * ? *)
            Description: Daily transaction scan
            Enabled: true
        MonthlySettlement:
          Type: Schedule
          Properties:
            Schedule: cron(0 10 1 * ? *)
            Description: Monthly settlement calculation
            Enabled: true

  WebhookFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub credit-card-tracker-webhook-${Environment}
      Handler: webhook.handler
      CodeUri: lambdas/
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref TransactionsBucket
      Events:
        TwilioWebhook:
          Type: Api
          Properties:
            Path: /sms
            Method: POST

Outputs:
  WebhookUrl:
    Description: Twilio webhook URL
    Value: !Sub https://${ServerlessRestApi}.execute-api.${AWS::Region}.amazonaws.com/Prod/sms
  S3Bucket:
    Description: S3 bucket for transaction data
    Value: !Ref TransactionsBucket
```

### Deploy Commands

```bash
# Build
sam build

# Deploy (first time)
sam deploy --guided

# Deploy (subsequent)
sam deploy
```

---

## Setup Prerequisites

### AWS
1. AWS account with IAM user/role
2. AWS CLI configured (`aws configure`)
3. SAM CLI installed (`brew install aws-sam-cli`)

### Plaid
1. Account at dashboard.plaid.com
2. Client ID and Secret from Keys page
3. Access Token (generate via Plaid Link or sandbox API)

**Sandbox Access Token (for testing):**
```bash
# Create sandbox item
curl -X POST https://sandbox.plaid.com/sandbox/public_token/create \
  -H 'Content-Type: application/json' \
  -d '{"client_id": "YOUR_ID", "secret": "YOUR_SECRET", "institution_id": "ins_109508", "initial_products": ["transactions"]}'

# Exchange for access token
curl -X POST https://sandbox.plaid.com/item/public_token/exchange \
  -H 'Content-Type: application/json' \
  -d '{"client_id": "YOUR_ID", "secret": "YOUR_SECRET", "public_token": "PUBLIC_TOKEN"}'
```

### Twilio
1. Account at twilio.com
2. Account SID and Auth Token from Console Dashboard
3. Phone number with SMS capability (~$1.15/month)
4. After deploy: Configure webhook URL in Phone Numbers settings

---

## EARS Specifications Reference

### Transaction Fetching (FETCH)
- **FETCH-001**: Fetch new transactions from Plaid daily
- **FETCH-002**: Append new transactions to CSV with empty classification
- **FETCH-003**: Do not create duplicates (check transaction_id)
- **FETCH-004**: Retry Plaid API up to 3 times with exponential backoff

### SMS Outbound (SMS-OUT)
- **SMS-OUT-001**: Send SMS to both users listing unclassified transactions
- **SMS-OUT-002**: Include transaction number, merchant, amount
- **SMS-OUT-003**: Include reply format instructions
- **SMS-OUT-004**: Do not send if no unclassified transactions

### SMS Inbound (SMS-IN)
- **SMS-IN-001**: Parse newline-delimited classification codes
- **SMS-IN-002**: Accept format: {number}{S|A|B}{optional percentage}
- **SMS-IN-003**: Case-insensitive
- **SMS-IN-004**: Skip invalid lines, continue parsing
- **SMS-IN-005**: Reply with format instructions if no valid classifications

### Classification (CLASS)
- **CLASS-001**: Update transaction in CSV when classified
- **CLASS-002**: Record who classified
- **CLASS-003**: Ignore if already classified
- **CLASS-004**: Notify other user of classification
- **CLASS-005**: Default shared to 50/50
- **CLASS-006**: Percentage is relative to classifier

### Monthly Settlement (SETTLE)
- **SETTLE-001**: Calculate on 1st of month for previous statement period
- **SETTLE-002**: Individual (A/B) = 100% to that user
- **SETTLE-003**: Shared splits per recorded percentage
- **SETTLE-004**: Send summary SMS to both users
- **SETTLE-005**: Show each user's total owed

### Error Handling (ERR)
- **ERR-001**: Retry Twilio send once on failure
- **ERR-002**: Return error response on S3 failure
- **ERR-003**: Reply with valid range for invalid transaction number

---

*This document contains all information needed to recreate the Credit Card Tracker project.*
