
import pytest
from lib import storage
from unittest.mock import MagicMock

@pytest.fixture
def mock_s3(mocker):
    mock = mocker.patch("lib.storage.get_s3_client")
    mock_client = MagicMock()
    mock.return_value = mock_client
    return mock_client

def test_update_transaction_note(mock_s3, mocker):
    # Setup initial data
    initial_csv = (
        "transaction_id,date,amount,merchant,classification,classified_by,percentage,notified_at,note\n"
        "txn_123,2023-10-01,100.00,Test Merchant,S,UserA,50,2023-10-01,\n"
    )
    
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: initial_csv.encode("utf-8"))
    }
    
    # Execute
    result = storage.update_transaction_note("txn_123", "Business lunch")
    
    # Verify
    assert result is True
    
    # Check S3 put_object call
    mock_s3.put_object.assert_called_once()
    call_args = mock_s3.put_object.call_args[1]
    saved_csv = call_args["Body"]
    
    assert "txn_123" in saved_csv
    assert "Business lunch" in saved_csv

def test_reset_transaction_clears_note(mock_s3, mocker):
    # Setup initial data with a note
    initial_csv = (
        "transaction_id,date,amount,merchant,classification,classified_by,percentage,notified_at,note\n"
        "txn_123,2023-10-01,100.00,Test Merchant,S,UserA,50,2023-10-01,Old Note\n"
    )
    
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: initial_csv.encode("utf-8"))
    }
    
    # Execute
    result = storage.reset_transaction("txn_123")
    
    # Verify
    assert result is True
    
    # Check S3 put_object call
    mock_s3.put_object.assert_called_once()
    call_args = mock_s3.put_object.call_args[1]
    saved_csv = call_args["Body"]
    
    # Note should be empty
    assert "Old Note" not in saved_csv
    # Classification should be empty
    assert ",,,,," in saved_csv or ",,," in saved_csv # rough check for empty fields

