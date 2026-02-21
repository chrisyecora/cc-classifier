import pytest
from lambdas.daily_scan import handler


def test_handler_daily_scan_cursor(mocker, env_setup):
    event = {"resources": ["arn:aws:events:us-east-1:123:rule/DailySchedule"]}

    # Mock Storage Cursor
    mocker.patch("lambdas.daily_scan.get_cursor", return_value="old_cursor")
    mock_save_cursor = mocker.patch("lambdas.daily_scan.save_cursor")

    # Mock Plaid
    mock_fetch = mocker.patch(
        "lambdas.daily_scan.fetch_new_transactions",
        return_value=(
            [{"transaction_id": "1", "amount": "10.00", "merchant": "Test"}],
            [],  # modified
            [],  # removed
            "new_cursor",
        ),
    )

    # Mock Storage
    mock_append = mocker.patch("lambdas.daily_scan.append_transactions", return_value=1)

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

    mock_fetch = mocker.patch("lambdas.daily_scan.fetch_new_transactions", return_value=([], [], [], "init_cursor"))
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

    mocker.patch("lambdas.daily_scan.format_settlement_message", return_value="Msg")
    mock_send = mocker.patch("lambdas.daily_scan.send_settlement_notification")

    handler(event, None)

    mock_calculate.assert_called()
    mock_send.assert_called()


def test_handler_unknown_event(mocker, env_setup):
    # Defaults to daily scan
    mocker.patch("lambdas.daily_scan.get_cursor", return_value=None)
    mocker.patch("lambdas.daily_scan.save_cursor")
    mocker.patch("lambdas.daily_scan.fetch_new_transactions", return_value=([], [], [], "c"))
    mocker.patch("lambdas.daily_scan.append_transactions", return_value=0)

    handler({"resources": ["unknown"]}, None)


def test_daily_scan_sends_error_notification_on_failure(mocker, env_setup):
    # Mock dependencies
    mocker.patch("lambdas.daily_scan.get_cursor", return_value="some_cursor")

    mock_fetch = mocker.patch("lambdas.daily_scan.fetch_new_transactions")
    mock_fetch.side_effect = Exception("Plaid API Error: Item Login Required")

    mock_send_error = mocker.patch("lambdas.daily_scan.send_error_notification")

    # Mock EventBridge event
    event = {"resources": ["arn:aws:events:rule/DailySchedule"]}

    # Run handler and expect exception
    with pytest.raises(Exception, match="Plaid API Error"):
        handler(event, None)

    # Assert
    mock_send_error.assert_called_once()
    args, _ = mock_send_error.call_args
    assert "Plaid API Error: Item Login Required" in args[0]


def test_monthly_settlement_sends_error_notification_on_failure(mocker, env_setup):
    # Mock dependencies
    mock_calc = mocker.patch("lambdas.daily_scan.calculate_settlement")
    mock_calc.side_effect = Exception("DynamoDB Error: ProvisionedThroughputExceeded")

    mock_send_error = mocker.patch("lambdas.daily_scan.send_error_notification")

    # Mock EventBridge event for monthly settlement
    event = {"resources": ["arn:aws:events:rule/MonthlySettlement"]}

    # Run handler and expect exception
    with pytest.raises(Exception, match="DynamoDB Error"):
        handler(event, None)

    # Assert
    mock_send_error.assert_called_once()
    args, _ = mock_send_error.call_args
    assert "DynamoDB Error: ProvisionedThroughputExceeded" in args[0]
