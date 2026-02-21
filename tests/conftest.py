import pytest
import boto3
from moto import mock_aws
from config import reset_config

@pytest.fixture
def env_setup(monkeypatch):
    """Set up environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "TABLE_NAME": "test-table",
        "AWS_DEFAULT_REGION": "us-east-1",
        "DISCORD_BOT_TOKEN": "test_bot_token",
        "DISCORD_PUBLIC_KEY": "00" * 32, # 32 bytes hex string (64 chars)
        "DISCORD_CLASSIFICATIONS_CHANNEL_ID": "111",
        "DISCORD_SETTLEMENTS_CHANNEL_ID": "222",
        "PLAID_CLIENT_ID": "plaidtest",
        "PLAID_SECRET": "plaidsecret",
        "PLAID_ACCESS_TOKEN": "access-sandbox-123",
        "USER_A_NAME": "TestAlex",
        "USER_B_NAME": "TestBeth",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    
    reset_config()
    yield
    reset_config()

@pytest.fixture
def dynamodb_mock(env_setup):
    """Mock DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        # Create the table with schema matching template.yaml
        table = dynamodb.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
                {"AttributeName": "date", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "DateIndex",
                    "KeySchema": [
                        {"AttributeName": "pk", "KeyType": "HASH"},
                        {"AttributeName": "date", "KeyType": "RANGE"}
                    ],
                    "Projection": {"ProjectionType": "ALL"}
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        yield table

# Alias for backward compatibility if tests request s3_mock (though we should update them)
# But we must update them because s3_mock returned an InMemoryS3 object, 
# while dynamodb_mock returns a boto3 Table resource.
# So I won't provide an alias, I'll force update of tests.

def read_transactions() -> list[dict]:
    from lib.storage import get_table, PK_TRX, _map_ddb_items_to_model
    from boto3.dynamodb.conditions import Key
    table = get_table()
    response = table.scan(
        FilterExpression=Key('pk').eq(PK_TRX)
    )
    items = response.get('Items', [])
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=Key('pk').eq(PK_TRX),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
        
    return _map_ddb_items_to_model(items)

def write_transactions(transactions: list[dict]) -> None:
    from lib.storage import get_table, _map_model_to_ddb_item
    table = get_table()
    with table.batch_writer() as batch:
        for txn in transactions:
            item = _map_model_to_ddb_item(txn)
            batch.put_item(Item=item)