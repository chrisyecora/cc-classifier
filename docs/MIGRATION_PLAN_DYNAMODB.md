# Implementation Plan: DynamoDB Architecture

## 1. Context
We are replacing the file-based S3 CSV storage with **AWS DynamoDB** (NoSQL) to ensure atomic updates, eliminate race conditions, and improve query performance before the project goes live.

**Assumption:** No existing data needs to be migrated. We are starting with an empty database.

---

## 2. Infrastructure Changes (`template.yaml`)

### 2.1. Add DynamoDB Table
We will define a single-table design with a Global Secondary Index (GSI) for date-based queries.

```yaml
  TransactionsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub credit-card-tracker-${Environment}
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
        - AttributeName: sk
          AttributeType: S
        - AttributeName: date
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH  # Partition Key
        - AttributeName: sk
          KeyType: RANGE # Sort Key
      GlobalSecondaryIndexes:
        - IndexName: DateIndex
          KeySchema:
            - AttributeName: pk
              KeyType: HASH
            - AttributeName: date
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
```

### 2.2. Remove S3 Bucket
*   Remove `TransactionsBucket` resource.
*   Remove `S3_BUCKET` environment variable from Globals.

### 2.3. Update Lambda Policies
*   Replace `S3CrudPolicy` with `DynamoDBCrudPolicy`:
    ```yaml
    Policies:
      - DynamoDBCrudPolicy:
          TableName: !Ref TransactionsTable
    ```
*   Add `TABLE_NAME` to environment variables.

---

## 3. Schema Design

We will use a generic Primary Key (`pk`) and Sort Key (`sk`) pattern.

| Item Type | PK (`pk`) | SK (`sk`) | Attributes | Access Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Transaction** | `TRX` | `{transaction_id}` | `date`, `amount`, `merchant`, `classification`, `excluded`, `note` | Get specific txn; Query all txns |
| **Cursor** | `CONFIG` | `PLAID_CURSOR` | `value` | Get/Set Plaid cursor |

*   **Date Queries:** Use `DateIndex` with `pk="TRX"` and `date` range to get transactions for monthly settlements.

---

## 4. Code Refactoring

### 4.1. `lib/storage.py` (Complete Rewrite)
*   **Init:** Initialize `boto3.resource('dynamodb')` and `Table`.
*   **`save_cursor(cursor)`:** `table.put_item(Item={'pk': 'CONFIG', 'sk': 'PLAID_CURSOR', 'value': cursor})`
*   **`get_cursor()`:** `table.get_item(...)`.
*   **`append_transactions(txns)`:**
    *   Iterate and use `table.batch_writer()`.
    *   Item structure: `{'pk': 'TRX', 'sk': txn['transaction_id'], ...txn_fields}`.
    *   *Note:* `batch_writer` automatically handles deduplication (overwrites by PK/SK), which is desired behavior here.
*   **`update_transaction(...)`:**
    *   Use `table.update_item` with `UpdateExpression` (e.g., `SET classification = :c, classified_by = :u`).
    *   **Benefit:** Atomic update. No need to read the full file first.
*   **`exclude_transaction(...)`:** Atomic update setting `excluded = "true"`.
*   **`get_transactions_for_statement_period(...)`:**
    *   Query `DateIndex`: `Key('pk').eq('TRX') & Key('date').between(start, end)`.

### 4.2. `lib/settlement.py`
*   Likely no changes needed if `storage.get_transactions_for_statement_period` returns the same list of dicts.

### 4.3. Tests
*   Update `conftest.py` (or `tests/conftest.py`) to use `moto`'s `mock_dynamodb`.
*   Replace `s3_mock` fixture with `dynamodb_mock`.
*   Create the table within the mock context before running tests.

---

## 5. Execution Checklist

1.  [ ] **Update `template.yaml`:** Swap S3 for DynamoDB resources and permissions.
2.  [ ] **Update Tests:** Refactor `tests/conftest.py` to mock DynamoDB. Verify tests fail (red).
3.  [ ] **Refactor `lib/storage.py`:** Implement DynamoDB logic.
4.  [ ] **Verify:** Run `pytest`. All tests should pass (green).
5.  [ ] **Deploy:** `sam build && sam deploy`.