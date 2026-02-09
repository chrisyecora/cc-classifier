"""Configuration management from environment variables."""
import os
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

        _config = Config(
            environment=get_env("ENVIRONMENT", "dev"),
            table_name=get_env("TABLE_NAME", ""),
            
            discord_bot_token=get_env("DISCORD_BOT_TOKEN", ""),
            discord_public_key=get_env("DISCORD_PUBLIC_KEY", ""),
            discord_classifications_channel_id=get_env("DISCORD_CLASSIFICATIONS_CHANNEL_ID", ""),
            discord_settlements_channel_id=get_env("DISCORD_SETTLEMENTS_CHANNEL_ID", ""),
            
            plaid_client_id=get_env("PLAID_CLIENT_ID", ""),
            plaid_secret=get_env("PLAID_SECRET", ""),
            plaid_access_token=get_env("PLAID_ACCESS_TOKEN", ""),
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