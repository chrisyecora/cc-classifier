import os
import pytest
from unittest.mock import MagicMock
import boto3
from config import reset_config

class InMemoryS3:
    def __init__(self):
        self.storage: dict[str, dict[str, str]] = {}
        # Mocking exceptions
        self.exceptions = type("Exceptions", (), {
            "NoSuchKey": type("NoSuchKey", (Exception,), {})
        })()

    def get_object(self, Bucket: str, Key: str) -> dict:
        if Bucket not in self.storage or Key not in self.storage[Bucket]:
            # Simulate AWS ClientError for NoSuchKey
            # In a real boto3 mock, this would be a botocore.exceptions.ClientError
            # For simplicity in our unit tests, we can raise a simpler exception 
            # or rely on the fact that we're mocking the client.
            # However, code often catches ClientError.
            # Let's try to mimic the structure if possible, or just raise a custom one 
            # if our code only catches Exception or ClientError.
            # Ideally we'd use botocore.exceptions.ClientError but that requires instantiating it complexly.
            # For now, let's raise a KeyError which we can verify/handle in tests, 
            # or better: raise a mocked ClientError.
            
            # Since we can't easily import botocore here without adding it to deps (it is in boto3 deps),
            # We will raise a simple exception for now, but in our `s3_mock` fixture we might need to be smarter.
            raise self.exceptions.NoSuchKey("An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist.")
        
        return {
            "Body": MagicMock(read=lambda: self.storage[Bucket][Key].encode("utf-8")),
            "ContentType": "text/csv"
        }

    def put_object(self, Bucket: str, Key: str, Body: str | bytes, ContentType: str = None) -> dict:
        if Bucket not in self.storage:
            self.storage[Bucket] = {}
        
        if isinstance(Body, bytes):
            self.storage[Bucket][Key] = Body.decode("utf-8")
        else:
            self.storage[Bucket][Key] = Body
            
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

@pytest.fixture
def env_setup(monkeypatch):
    """Set up environment variables for testing."""
    env_vars = {
        "ENVIRONMENT": "test",
        "S3_BUCKET": "test-bucket",
        "TWILIO_ACCOUNT_SID": "ACtest",
        "TWILIO_AUTH_TOKEN": "authtest",
        "TWILIO_PHONE_NUMBER": "+15550000000",
        "PLAID_CLIENT_ID": "plaidtest",
        "PLAID_SECRET": "plaidsecret",
        "PLAID_ACCESS_TOKEN": "access-sandbox-123",
        "USER_A_NAME": "TestAlex",
        "USER_A_PHONE": "+15551111111",
        "USER_B_NAME": "TestBeth",
        "USER_B_PHONE": "+15552222222",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    
    reset_config()
    yield
    reset_config()

@pytest.fixture
def s3_mock(mocker):
    """Mock boto3 S3 client with in-memory storage."""
    in_memory_s3 = InMemoryS3()
    
    def mock_client(service_name, **kwargs):
        if service_name == "s3":
            return in_memory_s3
        return MagicMock()

    mocker.patch("boto3.client", side_effect=mock_client)
    return in_memory_s3
