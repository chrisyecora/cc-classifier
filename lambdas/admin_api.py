"""Authenticated REST API for the statement review app."""

import json
from datetime import datetime, timezone
from decimal import Decimal

from config import get_config
from lib.discord_client import send_settlement_notification
from lib.statements import ConflictError, list_statements, save_period, statement_view
from lib.storage import admin_update_transaction, get_table, get_transaction


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)}")


def response(status: int, body: dict):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(body, default=_json_default),
    }


def handler(event, _context):
    method = event.get("httpMethod", "")
    path = event.get("path", "").rstrip("/")
    parts = path.strip("/").split("/")
    try:
        if method == "GET" and parts == ["api", "statements"]:
            return response(
                200,
                {
                    "statements": [
                        {
                            "month": item["sk"],
                            "start_date": item["start_date"],
                            "end_date": item["end_date"],
                            "revision": item.get("revision", 0),
                        }
                        for item in list_statements()
                    ]
                },
            )
        if len(parts) == 3 and parts[:2] == ["api", "statements"]:
            month = parts[2]
            if method == "GET":
                return response(200, statement_view(month))
            if method == "PUT":
                body = json.loads(event.get("body") or "{}")
                return response(200, save_period(month, body["start_date"], body["end_date"], int(body["version"])))
        if len(parts) == 4 and parts[:2] == ["api", "statements"] and parts[3] == "publish" and method == "POST":
            body = json.loads(event.get("body") or "{}")
            return response(200, publish(parts[2], int(body["version"])))
        if len(parts) == 3 and parts[:2] == ["api", "transactions"] and method == "PATCH":
            body = json.loads(event.get("body") or "{}")
            return response(200, update_transaction(parts[2], body))
        return response(404, {"error": "Not found"})
    except (KeyError, TypeError, json.JSONDecodeError, ValueError) as exc:
        return response(400, {"error": str(exc)})
    except ConflictError as exc:
        return response(409, {"error": str(exc)})
    except RuntimeError as exc:
        return response(502, {"error": str(exc)})


def update_transaction(transaction_id: str, body: dict) -> dict:
    txn = get_transaction(transaction_id)
    if not txn:
        raise ValueError("Transaction not found")
    classification = body["classification"]
    if classification not in ("", "A", "B", "S"):
        raise ValueError("Invalid classification")
    excluded = body["excluded"]
    if not isinstance(excluded, bool):
        raise TypeError("excluded must be boolean")
    note = body["note"]
    if not isinstance(note, str) or len(note) > 200:
        raise ValueError("Note must be at most 200 characters")
    percentage = body.get("percentage")
    payer = body.get("share_user")
    if classification == "S":
        if payer not in ("A", "B"):
            raise ValueError("Choose whose share percentage this is")
        try:
            pct = Decimal(str(percentage))
        except Exception as exc:
            raise ValueError("Invalid percentage") from exc
        if not pct.is_finite() or not 0 <= pct <= 100 or pct.as_tuple().exponent < -2:
            raise ValueError("Percentage must be between 0 and 100 with at most two decimals")
        percentage_value = str(pct)
        config = get_config()
        classified_by = config.user_a_name if payer == "A" else config.user_b_name
    else:
        if percentage not in (None, ""):
            raise ValueError("Percentage applies only to shared classifications")
        percentage_value = ""
        classified_by = "Admin" if classification else ""
    values = {
        "classification": classification,
        "classified_by": classified_by,
        "percentage": percentage_value,
        "excluded": "true" if excluded else "",
        "note": note,
    }
    return admin_update_transaction(transaction_id, values, int(body["version"]))


def publish(month: str, expected_version: int) -> dict:
    view = statement_view(month)
    if not view["confirmed"]:
        raise ValueError("Confirm the statement dates before publishing")
    if view["version"] != expected_version:
        raise ConflictError("Statement changed; reload before publishing")
    if view["totals"]["unclassified_count"]:
        raise ValueError("Classify or ignore all transactions before publishing")
    if view["published"] and not view["has_unpublished_changes"]:
        raise ValueError("These settlement totals and dates have already been published")
    revision = view["revision"] + 1
    label = f"{view['start_date']} to {view['end_date']}"
    title = "Settlement" if revision == 1 else f"Settlement revision {revision}"
    totals = view["totals"]
    message = f"**{title}: {month} ({label})**\n{totals['user_a_name']}: ${totals['user_a']}\n{totals['user_b_name']}: ${totals['user_b']}"
    if not send_settlement_notification(message):
        raise RuntimeError("Discord did not accept the settlement message")
    from botocore.exceptions import ClientError

    try:
        get_table().update_item(
            Key={"pk": "STATEMENT", "sk": month},
            UpdateExpression="SET published=:published, revision=:revision",
            ConditionExpression="version=:version AND revision=:previous",
            ExpressionAttributeValues={
                ":published": {
                    "start_date": view["start_date"],
                    "end_date": view["end_date"],
                    "totals": totals,
                    "at": datetime.now(timezone.utc).isoformat(),
                },
                ":revision": revision,
                ":version": expected_version,
                ":previous": view["revision"],
            },
        )
    except ClientError as exc:
        raise RuntimeError(
            "Discord may have posted, but saving publication failed; check the channel before retrying"
        ) from exc
    return statement_view(month)
