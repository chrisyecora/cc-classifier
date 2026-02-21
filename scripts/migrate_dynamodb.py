import boto3
import argparse
import sys

def migrate_table(source_table_name: str, target_table_name: str, region: str = 'us-east-1'):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    
    source_table = dynamodb.Table(source_table_name)
    target_table = dynamodb.Table(target_table_name)
    
    print(f"Scanning source table: {source_table_name}...")
    try:
        response = source_table.scan()
        items = response.get('Items', [])
    except Exception as e:
        print(f"Error reading from source table: {e}")
        sys.exit(1)
        
    while 'LastEvaluatedKey' in response:
        response = source_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
        
    print(f"Found {len(items)} items. Writing to target table: {target_table_name}...")
    
    if not items:
        print("No items to migrate.")
        return

    try:
        with target_table.batch_writer() as batch:
            for i, item in enumerate(items):
                batch.put_item(Item=item)
                if i > 0 and i % 100 == 0:
                    print(f"  Migrated {i} items...")
    except Exception as e:
        print(f"Error writing to target table: {e}")
        sys.exit(1)
        
    print(f"Successfully migrated all {len(items)} items!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate DynamoDB data between tables.')
    parser.add_argument('--source', required=True, help='Source DynamoDB Table Name')
    parser.add_argument('--target', required=True, help='Target DynamoDB Table Name')
    parser.add_argument('--region', default='us-east-1', help='AWS Region (default: us-east-1)')
    
    args = parser.parse_args()
    migrate_table(args.source, args.target, args.region)
