import pytest
from datetime import date
from lambdas.daily_scan import handler

def test_handler_daily_scan(mocker, env_setup):
    # Mock EventBridge event for Daily Schedule
    event = {
        "resources": ["arn:aws:events:us-east-1:123:rule/DailySchedule"]
    }
    
    # Mock dependencies
    mock_fetch = mocker.patch("lambdas.daily_scan.fetch_transactions", return_value=[
        {"transaction_id": "1", "amount": "10.00", "merchant": "Test"}
    ])
    mock_append = mocker.patch("lambdas.daily_scan.append_transactions", return_value=1)
    mock_get_unclassified = mocker.patch("lambdas.daily_scan.get_unclassified_transactions", return_value=[
        {"transaction_id": "1", "merchant": "Test", "amount": "10.00"}
    ])
    mock_send_notif = mocker.patch("lambdas.daily_scan.send_transaction_notification")
    mock_read_users = mocker.patch("lambdas.daily_scan.read_users", return_value={})
    
    # Run handler
    handler(event, None)
    
    # Verify flow
    mock_fetch.assert_called_once()
    mock_append.assert_called_once()
    mock_get_unclassified.assert_called_once()
    mock_send_notif.assert_called_once()

def test_handler_monthly_settlement(mocker, env_setup):
    # Mock EventBridge event for Monthly Settlement
    event = {
        "resources": ["arn:aws:events:us-east-1:123:rule/MonthlySettlement"]
    }
    
    # Mock dependencies
    mock_calculate = mocker.patch("lambdas.daily_scan.calculate_settlement")
    mock_calculate.return_value.unclassified_count = 0
    mock_calculate.return_value.user_a.total_owed = "100.00"
    mock_calculate.return_value.user_b.total_owed = "50.00"
    
    mock_format = mocker.patch("lambdas.daily_scan.format_settlement_sms", return_value="Settlement msg")
    mock_send_sms = mocker.patch("lambdas.daily_scan.send_sms")
    mock_read_users = mocker.patch("lambdas.daily_scan.read_users", return_value={
        "user_a": {"phone": "+1A"},
        "user_b": {"phone": "+1B"}
    })
    
    # Run handler
    handler(event, None)
    
    # Verify flow
    mock_calculate.assert_called_once()
    mock_format.assert_called_once()
    assert mock_send_sms.call_count == 2 # One for each user

def test_handler_unknown_event(mocker, env_setup):
    # Mock daily scan dependencies since it defaults to daily scan
    mocker.patch("lambdas.daily_scan.fetch_transactions", return_value=[])
    mocker.patch("lambdas.daily_scan.append_transactions", return_value=0)
    
    event = {"resources": ["unknown"]}
    # Should run daily scan
    handler(event, None)
    # No crash
