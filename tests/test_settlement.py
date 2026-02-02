from datetime import date
from decimal import Decimal
import pytest
from lib.settlement import calculate_settlement, SettlementResult, UserSettlement

# Dummy transaction structure for mocking
def make_transaction(amount, classification, percentage=None, classifier="Alex"):
    return {
        "amount": str(amount),
        "classification": classification,
        "percentage": str(percentage) if percentage else None,
        "classified_by": classifier
    }

def test_settlement_all_shared_50_50(mocker, env_setup):
    # Mock storage interactions
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        make_transaction(100.00, "S"),
        make_transaction(50.00, "S")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    # Total = 150. Split 50/50 -> 75 each.
    assert result.user_a.total_owed == Decimal("75.00")
    assert result.user_b.total_owed == Decimal("75.00")
    assert result.statement_start == date(2025, 12, 10)

def test_settlement_individual(mocker, env_setup):
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        make_transaction(100.00, "A"),  # Alex pays 100
        make_transaction(50.00, "B")    # Beth pays 50
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    assert result.user_a.total_owed == Decimal("100.00")
    assert result.user_b.total_owed == Decimal("50.00")

def test_settlement_custom_percentage(mocker, env_setup):
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        # Alex classified, Alex pays 70% of 100 -> Alex 70, Beth 30
        make_transaction(100.00, "S", percentage=70, classifier="TestAlex"),
        # Beth classified, Beth pays 20% of 50 -> Beth 10, Alex 40
        make_transaction(50.00, "S", percentage=20, classifier="TestBeth")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    
    # Alex: 70 + 40 = 110
    # Beth: 30 + 10 = 40
    assert result.user_a.total_owed == Decimal("110.00")
    assert result.user_b.total_owed == Decimal("40.00")

def test_settlement_unclassified_count(mocker, env_setup):
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        make_transaction(100.00, ""),
        make_transaction(50.00, "S")
    ])
    
    result = calculate_settlement(date(2026, 2, 1))
    assert result.unclassified_count == 1
    # Unclassified are ignored in total calculation for now, or should warn?
    # Spec doesn't explicitly say. Usually they should be alerted.
    # Logic: Ignore unclassified in sum, but report count.
    assert result.user_a.total_owed == Decimal("25.00") # 50 split
    assert result.user_b.total_owed == Decimal("25.00")

def test_rounding(mocker, env_setup):
    mocker.patch("lib.settlement.get_statement_period", return_value=(date(2025, 12, 10), date(2026, 1, 9)))
    mocker.patch("lib.settlement.get_transactions_for_statement_period", return_value=[
        make_transaction(0.01, "S") # 0.005 each -> round half up? or just round standard.
    ])
    # Decimal default rounding is ROUND_HALF_EVEN (Banker's).
    # 0.005 -> 0.00.
    
    result = calculate_settlement(date(2026, 2, 1))
    # We should define a rounding policy. Standard 2 decimal places.
    # If 0.01 split, someone pays 0.01, someone 0? Or 0.005 each.
    # Let's see what default Decimal implementation does.
