import pytest
from datetime import date
from lambdas.daily_scan import handler

def test_handler_daily_scan_cursor(mocker, env_setup):
    event = {"resources": ["arn:aws:events:us-east-1:123:rule/DailySchedule"]}
    
    # Mock Storage Cursor
    mocker.patch("lambdas.daily_scan.get_cursor", return_value="old_cursor")
    mock_save_cursor = mocker.patch("lambdas.daily_scan.save_cursor")
    
    # Mock Plaid
    mock_fetch = mocker.patch("lambdas.daily_scan.fetch_new_transactions", return_value=(
        [{"transaction_id": "1", "amount": "10.00", "merchant": "Test"}],
        "new_cursor"
    ))
    
    # Mock Storage
    mock_append = mocker.patch("lambdas.daily_scan.append_transactions", return_value=1)
    mock_get_unclassified = mocker.patch("lambdas.daily_scan.get_unclassified_transactions", return_value=[
        {"transaction_id": "1", "merchant": "Test", "amount": "10.00"}
    ])
    
    # Mock Notification
    mock_send_notif = mocker.patch("lambdas.daily_scan.send_transaction_notification")
    
    # Run
    handler(event, None)
    
    # Verify
    mock_fetch.assert_called_with("old_cursor")
    mock_save_cursor.assert_called_with("new_cursor")
    mock_append.assert_called()
    mock_send_notif.assert_called()

def test_handler_daily_scan_no_cursor_initial(mocker, env_setup):
    event = {"resources": ["arn:aws:events:us-east-1:123:rule/DailySchedule"]}
    
    mocker.patch("lambdas.daily_scan.get_cursor", return_value=None)
    mock_save_cursor = mocker.patch("lambdas.daily_scan.save_cursor")
    
    mock_fetch = mocker.patch("lambdas.daily_scan.fetch_new_transactions", return_value=(
        [], "init_cursor"
    ))
    mocker.patch("lambdas.daily_scan.append_transactions", return_value=0)
    
    handler(event, None)
    
    mock_fetch.assert_called_with(None)
    mock_save_cursor.assert_called_with("init_cursor")

def test_handler_monthly_settlement(mocker, env_setup):
    event = {"resources": ["arn:aws:events:us-east-1:123:rule/MonthlySettlement"]}
    
    # Mock Settlement Logic (unchanged)
    mock_calculate = mocker.patch("lambdas.daily_scan.calculate_settlement")
    mock_calculate.return_value.unclassified_count = 0
    mock_calculate.return_value.user_a.total_owed = "100.00"
    mock_calculate.return_value.user_b.total_owed = "50.00"
    
    mock_format = mocker.patch("lambdas.daily_scan.format_settlement_sms", return_value="Msg")
    mock_send = mocker.patch("lambdas.daily_scan.send_settlement_notification")
    
    handler(event, None)
    
    mock_calculate.assert_called()
    mock_send.assert_called()

def test_handler_unknown_event(mocker, env_setup):
    # Defaults to daily scan
    mocker.patch("lambdas.daily_scan.get_cursor", return_value=None)
    mocker.patch("lambdas.daily_scan.save_cursor")
    mocker.patch("lambdas.daily_scan.fetch_new_transactions", return_value=([], "c"))
    mocker.patch("lambdas.daily_scan.append_transactions", return_value=0)
    
    handler({"resources": ["unknown"]}, None)
