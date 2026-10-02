"""Statement drafts, review state, and publication snapshots."""

import re
from datetime import date, timedelta
from decimal import Decimal

from boto3.dynamodb.conditions import Key

from lib.settlement import calculate_for_transactions
from lib.storage import get_table, get_transactions_between

PK_STATEMENT = "STATEMENT"
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ConflictError(Exception):
    pass


def valid_month(month: str) -> date:
    if not MONTH_RE.fullmatch(month):
        raise ValueError("Statement month must be YYYY-MM")
    return date.fromisoformat(f"{month}-01")


def list_statements() -> list[dict]:
    table = get_table()
    items = []
    kwargs = {"KeyConditionExpression": Key("pk").eq(PK_STATEMENT)}
    while True:
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    return sorted(items, key=lambda item: item["sk"], reverse=True)


def get_saved_statement(month: str) -> dict | None:
    valid_month(month)
    return get_table().get_item(Key={"pk": PK_STATEMENT, "sk": month}, ConsistentRead=True).get("Item")


def proposed_period(month: str) -> tuple[date, date]:
    first = valid_month(month)
    end = first.replace(day=9)
    previous = [s for s in list_statements() if s["sk"] < month and s.get("confirmed")]
    if previous:
        start = date.fromisoformat(previous[0]["end_date"]) + timedelta(days=1)
    else:
        prior_month_last = first - timedelta(days=1)
        start = prior_month_last.replace(day=10)
    return start, end


def statement_view(month: str) -> dict:
    saved = get_saved_statement(month)
    if saved:
        start, end = date.fromisoformat(saved["start_date"]), date.fromisoformat(saved["end_date"])
    else:
        start, end = proposed_period(month)
    transactions = sorted(
        get_transactions_between(start, end), key=lambda t: (t["date"], t["transaction_id"]), reverse=True
    )
    result = calculate_for_transactions(start, end, transactions)
    published = saved.get("published") if saved else None
    totals = {
        "user_a_name": result.user_a.user_name,
        "user_a": str(result.user_a.total_owed),
        "user_b_name": result.user_b.user_name,
        "user_b": str(result.user_b.total_owed),
        "unclassified_count": result.unclassified_count,
    }
    return {
        "month": month,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "confirmed": bool(saved and saved.get("confirmed")),
        "version": int(saved.get("version", 0)) if saved else 0,
        "revision": int(saved.get("revision", 0)) if saved else 0,
        "published": published,
        "has_unpublished_changes": bool(
            published
            and (
                published.get("start_date") != start.isoformat()
                or published.get("end_date") != end.isoformat()
                or published.get("totals") != totals
            )
        ),
        "totals": totals,
        "transactions": transactions,
    }


def save_period(month: str, start_text: str, end_text: str, expected_version: int) -> dict:
    valid_month(month)
    start, end = date.fromisoformat(start_text), date.fromisoformat(end_text)
    if start > end or end.strftime("%Y-%m") != month:
        raise ValueError("Dates must be ordered and the end date must fall in the statement month")
    others = list_statements()
    for other in others:
        if other["sk"] == month:
            continue
        other_start, other_end = date.fromisoformat(other["start_date"]), date.fromisoformat(other["end_date"])
        if start <= other_end and other_start <= end:
            raise ValueError(f"Period overlaps statement {other['sk']}")
    first = valid_month(month)
    prior_month = (first - timedelta(days=1)).strftime("%Y-%m")
    next_month = (first.replace(day=28) + timedelta(days=4)).strftime("%Y-%m")
    adjacent = {item["sk"]: item for item in others if item.get("confirmed")}
    if prior_month in adjacent and start != date.fromisoformat(adjacent[prior_month]["end_date"]) + timedelta(days=1):
        raise ValueError("Start must follow the previous statement's end date")
    if next_month in adjacent and end + timedelta(days=1) != date.fromisoformat(adjacent[next_month]["start_date"]):
        raise ValueError("End must precede the next statement's start date")
    table = get_table()
    saved = get_saved_statement(month)
    if (int(saved.get("version", 0)) if saved else 0) != expected_version:
        raise ConflictError("Statement changed; reload before saving")
    from botocore.exceptions import ClientError

    try:
        if saved:
            table.update_item(
                Key={"pk": PK_STATEMENT, "sk": month},
                UpdateExpression="SET start_date=:s, end_date=:e, confirmed=:c, version=:next",
                ConditionExpression="version=:old",
                ExpressionAttributeValues={
                    ":s": start_text,
                    ":e": end_text,
                    ":c": True,
                    ":next": expected_version + 1,
                    ":old": expected_version,
                },
            )
        else:
            table.put_item(
                Item={
                    "pk": PK_STATEMENT,
                    "sk": month,
                    "start_date": start_text,
                    "end_date": end_text,
                    "confirmed": True,
                    "version": 1,
                    "revision": 0,
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConflictError("Statement changed; reload before saving") from exc
        raise
    return statement_view(month)


def totals_as_decimals(view: dict) -> tuple[Decimal, Decimal]:
    return Decimal(view["totals"]["user_a"]), Decimal(view["totals"]["user_b"])
