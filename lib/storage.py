import boto3
from boto3.dynamodb.conditions import Key
from datetime import date
from dateutil.relativedelta import relativedelta
from config import get_config

# Constants
PK_TRX = "TRX"
PK_CONFIG = "CONFIG"
SK_CURSOR = "PLAID_CURSOR"

def get_table():
    config = get_config()
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(config.table_name)

def get_transaction(transaction_id: str) -> dict | None:
    """
    Retrieves a single transaction by ID.
    """
    table = get_table()
    response = table.get_item(Key={'pk': PK_TRX, 'sk': transaction_id})
    item = response.get('Item')
    if item:
        return _map_ddb_items_to_model([item])[0]
    return None

def read_transactions() -> list[dict]:
    """
    Reads all transactions. 
    Warning: This performs a Scan operation.
    """
    table = get_table()
    response = table.scan(
        FilterExpression=Key('pk').eq(PK_TRX)
    )
    items = response.get('Items', [])
    
    # Handle pagination if > 1MB (unlikely for personal use but good practice)
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Key('pk').eq(PK_TRX),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
        
    return _map_ddb_items_to_model(items)

def write_transactions(transactions: list[dict]) -> None:
    """
    Overwrites/Inserts transactions.
    """
    table = get_table()
    with table.batch_writer() as batch:
        for txn in transactions:
            item = _map_model_to_ddb_item(txn)
            batch.put_item(Item=item)

def append_transactions(new_transactions: list[dict]) -> int:
    """
    Appends new transactions using TransactWriteItems for efficiency.
    Falls back to individual put_items if the transaction batch has collisions.
    """
    if not new_transactions:
        return 0
    
    table = get_table()
    dynamodb_client = boto3.client('dynamodb', region_name=table.meta.client.meta.region_name)
    config = get_config()
    table_name = config.table_name
    
    from boto3.dynamodb.types import TypeSerializer
    serializer = TypeSerializer()
    
    count = 0
    for i in range(0, len(new_transactions), 100):
        batch = new_transactions[i:i+100]
        transact_items = []
        for txn in batch:
            item = _map_model_to_ddb_item(txn)
            marshalled_item = {k: serializer.serialize(v) for k, v in item.items()}
            transact_items.append({
                'Put': {
                    'TableName': table_name,
                    'Item': marshalled_item,
                    'ConditionExpression': 'attribute_not_exists(sk)'
                }
            })
            
        try:
            dynamodb_client.transact_write_items(TransactItems=transact_items)
            count += len(batch)
        except dynamodb_client.exceptions.TransactionCanceledException:
            # Fallback to individual put_item for this batch
            for txn in batch:
                item = _map_model_to_ddb_item(txn)
                try:
                    table.put_item(
                        Item=item,
                        ConditionExpression="attribute_not_exists(sk)"
                    )
                    count += 1
                except dynamodb_client.exceptions.ConditionalCheckFailedException:
                    pass
            
    return count

def update_transaction(transaction_id: str, classification: str, classified_by: str, percentage: int | None) -> bool:
    table = get_table()
    
    # Check if already classified to avoid overwrite? 
    # Logic in old storage: if txn["classification"]: return False
    
    # We can use ConditionExpression
    try:
        table.update_item(
            Key={'pk': PK_TRX, 'sk': transaction_id},
            UpdateExpression="set classification=:c, classified_by=:u, percentage=:p",
            ConditionExpression="(attribute_not_exists(classification) OR classification = :empty) AND attribute_exists(pk)",
            ExpressionAttributeValues={
                ':c': classification,
                ':u': classified_by,
                ':p': str(percentage) if percentage is not None else "",
                ':empty': ""
            }
        )
        return True
    except boto3.client('dynamodb').exceptions.ConditionalCheckFailedException:
        return False

def exclude_transaction(transaction_id: str) -> bool:
    table = get_table()
    try:
        table.update_item(
            Key={'pk': PK_TRX, 'sk': transaction_id},
            UpdateExpression="set excluded=:e",
            ConditionExpression="attribute_exists(pk)",
            ExpressionAttributeValues={':e': "true"}
        )
        return True
    except Exception as e:
        print(f"Error excluding transaction {transaction_id}: {e}")
        return False

def update_transaction_note(transaction_id: str, note: str) -> bool:
    table = get_table()
    try:
        table.update_item(
            Key={'pk': PK_TRX, 'sk': transaction_id},
            UpdateExpression="set note=:n",
            ConditionExpression="attribute_exists(pk)",
            ExpressionAttributeValues={':n': note}
        )
        return True
    except Exception as e:
        print(f"Error updating note for {transaction_id}: {e}")
        return False

def reset_transaction(transaction_id: str) -> bool:
    table = get_table()
    try:
        table.update_item(
            Key={'pk': PK_TRX, 'sk': transaction_id},
            UpdateExpression="set classification=:e, classified_by=:e, percentage=:e, note=:e, excluded=:e",
            ConditionExpression="attribute_exists(pk)",
            ExpressionAttributeValues={':e': ""}
        )
        return True
    except Exception as e:
        print(f"Error resetting transaction {transaction_id}: {e}")
        return False

def delete_transaction(transaction_id: str) -> bool:
    """
    Deletes a transaction by ID.
    """
    table = get_table()
    try:
        table.delete_item(
            Key={'pk': PK_TRX, 'sk': transaction_id}
        )
        return True
    except Exception as e:
        print(f"Error deleting transaction {transaction_id}: {e}")
        return False

def update_transaction_details(transaction_id: str, amount: str, date_val: str, merchant: str, name: str) -> bool:
    """
    Updates transaction details from Plaid (amount, date, merchant, name)
    without modifying classification status.
    """
    table = get_table()
    try:
        table.update_item(
            Key={'pk': PK_TRX, 'sk': transaction_id},
            UpdateExpression="set amount=:a, #d=:d, merchant=:m, #n=:n",
            ExpressionAttributeNames={
                '#d': 'date',
                '#n': 'name'
            },
            ExpressionAttributeValues={
                ':a': amount,
                ':d': date_val,
                ':m': merchant,
                ':n': name
            },
            ConditionExpression="attribute_exists(pk)"
        )
        return True
    except Exception as e:
        print(f"Error updating transaction details {transaction_id}: {e}")
        return False

def get_statement_period(settlement_date: date) -> tuple[date, date]:
    # Same logic as before
    prev_month = settlement_date - relativedelta(months=1)
    end_date = date(prev_month.year, prev_month.month, 9)
    start_month = prev_month - relativedelta(months=1)
    start_date = date(start_month.year, start_month.month, 10)
    return start_date, end_date

def get_transactions_for_statement_period(settlement_date: date) -> list[dict]:
    start_date, end_date = get_statement_period(settlement_date)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    
    table = get_table()
    response = table.query(
        IndexName='DateIndex',
        KeyConditionExpression=Key('pk').eq(PK_TRX) & Key('date').between(start_str, end_str)
    )
    
    return _map_ddb_items_to_model(response.get('Items', []))

# --- Helpers ---

def _map_model_to_ddb_item(txn: dict) -> dict:
    item = txn.copy()
    item['pk'] = PK_TRX
    item['sk'] = txn['transaction_id']
    # DynamoDB doesn't like empty strings in some versions, but boto3 handles it mostly. 
    # If using older boto3/dynamodb, might need to use NULL or omit.
    # We will just pass it through for now.
    return item

def _map_ddb_items_to_model(items: list[dict]) -> list[dict]:
    result = []
    for item in items:
        # Convert Decimals to float/str if needed?
        # The app uses strings for amounts mostly.
        # boto3 Unmarshal handles Decimal.
        # Ensure 'transaction_id' is present (it is sk)
        if 'transaction_id' not in item and 'sk' in item:
            item['transaction_id'] = item['sk']
            
        if 'pk' in item: del item['pk']
        if 'sk' in item: del item['sk']
        
        result.append(item)
    return result

# --- User Config (Read-only from Config) ---

def read_users() -> dict[str, dict]:
    config = get_config()
    return {
        "user_a": {"name": config.user_a_name},
        "user_b": {"name": config.user_b_name}
    }

# --- Cursor Management ---

def get_cursor() -> str | None:
    table = get_table()
    response = table.get_item(Key={'pk': PK_CONFIG, 'sk': SK_CURSOR})
    if 'Item' in response:
        return response['Item'].get('value')
    return None

def save_cursor(cursor: str) -> None:
    if not cursor: return
    table = get_table()
    table.put_item(Item={'pk': PK_CONFIG, 'sk': SK_CURSOR, 'value': cursor})