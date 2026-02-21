"""Configuration management from environment variables and AWS Secrets Manager."""
import os
import json
import boto3
from dataclasses import dataclass

@dataclass
class Config:
    environment: str
    table_name: str
    
    # Discord
    discord_bot_token: str
    discord_public_key: str
    discord_classifications_channel_id: str
    discord_settlements_channel_id: str
    
    # Plaid
    plaid_client_id: str
    plaid_secret: str
    plaid_access_token: str
    plaid_env: str
    
    # Users
    user_a_name: str
    user_b_name: str
    discord_user_a: str
    discord_user_b: str

_config: Config | None = None

def get_config() -> Config:
    global _config
    if _config is None:
        def get_env(key, default=""):
            val = os.environ.get(key, default)
            return val.strip() if val else val

        env = get_env("ENVIRONMENT", "dev")

        # Load secrets from AWS Secrets Manager if not in test
        secrets = {}
        if env != "test" and not get_env("LOCAL_BYPASS_SECRETS"):
            try:
                secret_id = get_env("SECRET_ID", f"cc-classifier/{env}/secrets")
                client = boto3.client("secretsmanager")
                response = client.get_secret_value(SecretId=secret_id)
                secrets = json.loads(response["SecretString"])
            except Exception as e:
                print(f"Warning: Failed to load secrets from Secrets Manager: {e}")

        def get_secret_or_env(key):
            # Try secret first, then env var
            return secrets.get(key, get_env(key, ""))

        _config = Config(
            environment=env,
            table_name=get_env("TABLE_NAME", ""),
            
            discord_bot_token=get_secret_or_env("DISCORD_BOT_TOKEN"),
            discord_public_key=get_secret_or_env("DISCORD_PUBLIC_KEY"),
            discord_classifications_channel_id=get_env("DISCORD_CLASSIFICATIONS_CHANNEL_ID", ""),
            discord_settlements_channel_id=get_env("DISCORD_SETTLEMENTS_CHANNEL_ID", ""),
            
            plaid_client_id=get_secret_or_env("PLAID_CLIENT_ID"),
            plaid_secret=get_secret_or_env("PLAID_SECRET"),
            plaid_access_token=get_secret_or_env("PLAID_ACCESS_TOKEN"),
            plaid_env=get_env("PLAID_ENV", "sandbox"),
            
            user_a_name=get_env("USER_A_NAME", "Alex"),
            user_b_name=get_env("USER_B_NAME", "Beth"),
            discord_user_a=get_env("DISCORD_USER_A", ""),
            discord_user_b=get_env("DISCORD_USER_B", ""),
        )
    return _config

def reset_config() -> None:
    global _config
    _config = None