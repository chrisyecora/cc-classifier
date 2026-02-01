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
            s3_bucket=os.environ.get("S3_BUCKET", ""),
            twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.environ.get("TWILIO_AUTH_TOKEN", ""),
            twilio_phone_number=os.environ.get("TWILIO_PHONE_NUMBER", ""),
            plaid_client_id=os.environ.get("PLAID_CLIENT_ID", ""),
            plaid_secret=os.environ.get("PLAID_SECRET", ""),
            plaid_access_token=os.environ.get("PLAID_ACCESS_TOKEN", ""),
            user_a_name=os.environ.get("USER_A_NAME", "Alex"),
            user_a_phone=os.environ.get("USER_A_PHONE", ""),
            user_b_name=os.environ.get("USER_B_NAME", "Beth"),
            user_b_phone=os.environ.get("USER_B_PHONE", ""),
        )
    return _config

def reset_config() -> None:
    global _config
    _config = None
