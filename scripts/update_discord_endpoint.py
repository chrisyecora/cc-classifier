import sys
import boto3
import requests

import os

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config


def update_discord_endpoint(stack_name: str, region: str = "us-east-1"):
    # 1. Get the endpoint URL from CloudFormation stack outputs
    cloudformation = boto3.client("cloudformation", region_name=region)
    try:
        response = cloudformation.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0].get("Outputs", [])

        endpoint_url = None
        for output in outputs:
            if output["OutputKey"] == "InteractionsEndpointUrl":
                endpoint_url = output["OutputValue"]
                break

        if not endpoint_url:
            print("Error: Could not find InteractionsEndpointUrl in stack outputs.")
            sys.exit(1)

        print(f"Found Endpoint URL: {endpoint_url}")

    except Exception as e:
        print(f"Error describing stack {stack_name}: {e}")
        sys.exit(1)

    # 2. Get Discord Bot Token from config
    os.environ["ENVIRONMENT"] = "prod"
    config = get_config()
    bot_token = config.discord_bot_token

    if not bot_token:
        print("Error: Discord Bot Token not found in configuration.")
        sys.exit(1)

    # 3. Update Discord Application
    print("Updating Discord Application...")
    url = "https://discord.com/api/v10/applications/@me"
    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}
    payload = {"interactions_endpoint_url": endpoint_url}

    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Successfully updated Discord Interactions Endpoint URL!")
    except requests.exceptions.RequestException as e:
        print(f"Failed to update Discord endpoint: {e}")
        if e.response is not None:
            print(f"Discord API Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update Discord Interactions Endpoint URL.")
    parser.add_argument("--stack-name", required=True, help="CloudFormation Stack Name")
    parser.add_argument("--region", default="us-east-1", help="AWS Region")

    args = parser.parse_args()
    update_discord_endpoint(args.stack_name, args.region)
