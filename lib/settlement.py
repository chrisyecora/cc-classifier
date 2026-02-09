from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from lib.storage import get_transactions_for_statement_period, get_statement_period
from config import get_config

@dataclass
class UserSettlement:
    user_id: str
    user_name: str
    total_owed: Decimal
    transaction_count: int

@dataclass
class SettlementResult:
    statement_start: date
    statement_end: date
    user_a: UserSettlement
    user_b: UserSettlement
    unclassified_count: int

def calculate_settlement(settlement_date: date) -> SettlementResult:
    config = get_config()
    start_date, end_date = get_statement_period(settlement_date)
    transactions = get_transactions_for_statement_period(settlement_date)
    
    user_a_total = Decimal("0.00")
    user_b_total = Decimal("0.00")
    user_a_count = 0
    user_b_count = 0
    unclassified_count = 0
    
    for txn in transactions:
        if txn.get("excluded") == "true":
            continue

        amount = Decimal(str(txn["amount"]))
        classification = txn["classification"]
        
        if not classification:
            unclassified_count += 1
            continue
            
        if classification == "A":
            user_a_total += amount
            user_a_count += 1
        elif classification == "B":
            user_b_total += amount
            user_b_count += 1
        elif classification == "S":
            # Shared
            classifier = txn.get("classified_by")
            percentage_val = txn.get("percentage")
            
            if percentage_val:
                pct = Decimal(str(percentage_val)) / Decimal("100")
                classifier_share = amount * pct
                other_share = amount - classifier_share
                
                # Determine who is classifier
                # We need to match classifier name to user name in config
                # Assuming "TestAlex" in tests matches config user name
                # Real implementation needs robust name matching or ID
                
                # Simple name matching for now
                if classifier == config.user_a_name or classifier == config.discord_user_a:
                    user_a_total += classifier_share
                    user_b_total += other_share
                elif classifier == config.user_b_name or classifier == config.discord_user_b:
                    user_b_total += classifier_share
                    user_a_total += other_share
                else:
                    # Fallback if unknown classifier (should not happen in valid data)
                    # Split 50/50
                    half = amount / Decimal("2")
                    user_a_total += half
                    user_b_total += half
            else:
                # 50/50 split
                half = amount / Decimal("2")
                user_a_total += half
                user_b_total += half
                
            # Shared counts for both? Or just 1 total?
            # Let's count for both as "involvement"
            user_a_count += 1
            user_b_count += 1

    # Round totals
    user_a_total = user_a_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    user_b_total = user_b_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    return SettlementResult(
        statement_start=start_date,
        statement_end=end_date,
        user_a=UserSettlement(
            user_id="user_a", # Placeholder ID
            user_name=config.user_a_name,
            total_owed=user_a_total,
            transaction_count=user_a_count
        ),
        user_b=UserSettlement(
            user_id="user_b",
            user_name=config.user_b_name,
            total_owed=user_b_total,
            transaction_count=user_b_count
        ),
        unclassified_count=unclassified_count
    )

def format_settlement_sms(result: SettlementResult) -> str:
    import os
    is_dry_run = os.environ.get("IS_DRY_RUN", "false").lower() == "true"
    
    title = f"Settlement ({result.statement_start:%b %d}-{result.statement_end:%b %d})"
    if is_dry_run:
        title += " [DRY RUN]"
        
    msg = (
        f"**{title}**\n"
        f"{result.user_a.user_name}: ${result.user_a.total_owed:,.2f}\n"
        f"{result.user_b.user_name}: ${result.user_b.total_owed:,.2f}"
    )
    if result.unclassified_count > 0:
        msg += f"\n⚠️ WARNING: {result.unclassified_count} unclassified items excluded!"
    return msg
