
from datetime import date
from decimal import Decimal
import pytest
from lib.settlement import calculate_settlement, SettlementResult

def make_transaction(amount, classification, percentage=None, classifier="chrisy076"):
    return {
        "amount": str(amount),
        "classification": classification,
        "percentage": str(percentage) if percentage else None,
        "classified_by": classifier,
        "date": "2026-01-01",
        "merchant": "Test"
    }

def test_settlement_discord_username_user_a(mocker):
    # Setup Config with "Chris" AND discord_user_a="chrisy076"
    mocker.patch("lib.settlement.get_config", return_value=mocker.Mock(
        user_a_name="Chris",
        user_b_name="Beth",
        discord_user_a="chrisy076",
        discord_user_b="bethy123",
        s3_bucket="bucket"
    ))
    
    # Mock storage
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        # Chris (chrisy076) pays 100% of 100 -> Expect Chris=100, Beth=0
        make_transaction(100.00, "S", percentage=100, classifier="chrisy076")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    assert result.user_a.total_owed == Decimal("100.00")
    assert result.user_b.total_owed == Decimal("0.00")

def test_settlement_discord_username_user_b(mocker):
    mocker.patch("lib.settlement.get_config", return_value=mocker.Mock(
        user_a_name="Chris",
        user_b_name="Beth",
        discord_user_a="chrisy076",
        discord_user_b="bethy123",
        s3_bucket="bucket"
    ))
    
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        # Beth (bethy123) pays 100% of 50 -> Expect Chris=0, Beth=50
        make_transaction(50.00, "S", percentage=100, classifier="bethy123")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    assert result.user_a.total_owed == Decimal("0.00")
    assert result.user_b.total_owed == Decimal("50.00")

def test_settlement_unknown_username_fallback(mocker):
    mocker.patch("lib.settlement.get_config", return_value=mocker.Mock(
        user_a_name="Chris",
        user_b_name="Beth",
        discord_user_a="chrisy076",
        discord_user_b="bethy123",
        s3_bucket="bucket"
    ))
    
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        # Unknown user "randomUser" -> Expect 50/50 split of 100
        make_transaction(100.00, "S", percentage=100, classifier="randomUser")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    assert result.user_a.total_owed == Decimal("50.00")
    assert result.user_b.total_owed == Decimal("50.00")

