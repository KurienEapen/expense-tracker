import re
from datetime import datetime
from typing import Optional
import logging

from app.parser.models import ParsedTransaction
from app.parser.normalizer import (
    amount_to_paise,
    clean_merchant,
    normalize_sender,
    parse_date,
)
from app.parser.registry import CompiledTemplate, get_registry

logger = logging.getLogger(__name__)

# Fallback generic transaction patterns
GENERIC_AMOUNT_REGEX = re.compile(
    r"(?:Rs\.?|INR|₹)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE
)
GENERIC_CARD_LAST4_REGEX = re.compile(
    r"(?:card|a/c|acct|ending|xx|XX)[^\d]{0,10}(\d{4})",
    re.IGNORECASE
)
GENERIC_MERCHANT_REGEX = re.compile(
    r"(?:at|to|via)\s+([A-Za-z0-9\s&'\.-]{3,30}?)(?:\s+(?:on|Avl|ref|bal|using)|\.|$)",
    re.IGNORECASE
)

def parse_with_template(
    compiled: CompiledTemplate,
    body: str,
    received_at: Optional[datetime] = None
) -> Optional[ParsedTransaction]:
    """
    Attempts to match and extract transaction details using a compiled template.
    """
    match = compiled.compiled_regex.search(body)
    if not match:
        return None

    t_def = compiled.definition
    groups = t_def.groups

    # 1. Amount extraction
    amount_paise = 0
    if "amount" in groups and groups["amount"] <= len(match.groups()):
        raw_amt = match.group(groups["amount"])
        amount_paise = amount_to_paise(raw_amt)

    # 2. Card last 4 extraction
    card_last4 = None
    if "card_last4" in groups and groups["card_last4"] <= len(match.groups()):
        raw_last4 = match.group(groups["card_last4"])
        if raw_last4:
            # Strip non-digits in case regex included prefixes
            card_last4 = re.sub(r"\D", "", raw_last4)[-4:]

    # 3. Merchant extraction
    merchant_raw = None
    merchant_clean_val = None
    if "merchant" in groups and groups["merchant"] <= len(match.groups()):
        merchant_raw = match.group(groups["merchant"])
        merchant_clean_val = clean_merchant(merchant_raw)

    # 4. Date extraction
    transacted_at = received_at or datetime.utcnow()
    if "txn_date" in groups and groups["txn_date"] <= len(match.groups()):
        raw_date = match.group(groups["txn_date"])
        transacted_at = parse_date(raw_date, default_dt=received_at)

    return ParsedTransaction(
        issuer=t_def.issuer,
        card_type=t_def.card_type,
        card_last4=card_last4,
        transaction_type=t_def.transaction_type,
        amount_paise=amount_paise,
        currency="INR",
        merchant_raw=merchant_raw,
        merchant_clean=merchant_clean_val,
        category=t_def.category_override,
        transacted_at_utc=transacted_at,
        parsed_by_template_id=t_def.id,
        parser_confidence=1.0,
        status="settled",
    )

def parse_with_fallback(
    sender: str,
    body: str,
    received_at: Optional[datetime] = None
) -> Optional[ParsedTransaction]:
    """
    Generic heuristic fallback parser for non-templated or unknown bank notifications.
    """
    amt_match = GENERIC_AMOUNT_REGEX.search(body)
    if not amt_match:
        return None

    amount_paise = amount_to_paise(amt_match.group(1))
    if amount_paise <= 0:
        return None

    # Detect transaction type
    lower_body = body.lower()
    if any(k in lower_body for k in ["debited", "spent", "paid", "withdrawn", "sent"]):
        txn_type = "debit"
    elif any(k in lower_body for k in ["credited", "received", "refund", "cashback"]):
        txn_type = "credit"
    else:
        txn_type = "debit"

    # Card last 4
    card_last4 = None
    card_match = GENERIC_CARD_LAST4_REGEX.search(body)
    if card_match:
        card_last4 = card_match.group(1)

    # Merchant
    merchant_raw = None
    merchant_clean_val = None
    merch_match = GENERIC_MERCHANT_REGEX.search(body)
    if merch_match:
        merchant_raw = merch_match.group(1).strip()
        merchant_clean_val = clean_merchant(merchant_raw)

    norm_sender = normalize_sender(sender)
    issuer = norm_sender if norm_sender else "Unknown"

    return ParsedTransaction(
        issuer=issuer,
        card_type="credit" if "credit" in lower_body else "debit" if "debit" in lower_body else "account",
        card_last4=card_last4,
        transaction_type=txn_type,
        amount_paise=amount_paise,
        currency="INR",
        merchant_raw=merchant_raw,
        merchant_clean=merchant_clean_val,
        category=None,
        transacted_at_utc=received_at or datetime.utcnow(),
        parsed_by_template_id="generic_fallback",
        parser_confidence=0.5,
        status="settled",
    )

def parse_message(
    sender: str,
    body: str,
    received_at: Optional[datetime] = None
) -> Optional[ParsedTransaction]:
    """
    Main parsing orchestrator:
    1. Try templates matching the normalized sender.
    2. Try all other registered templates if sender didn't match.
    3. Run generic fallback parser if amount pattern is present.
    4. Return None if not a financial transaction message (e.g. OTP, promo).
    """
    registry = get_registry()

    # Step 1: Sender-specific template match
    sender_templates = registry.get_templates_for_sender(sender)
    for compiled in sender_templates:
        result = parse_with_template(compiled, body, received_at)
        if result:
            return result

    # Step 2: Global templates match (handles mismatched sender codes)
    for compiled in registry.get_all_templates():
        if compiled in sender_templates:
            continue
        result = parse_with_template(compiled, body, received_at)
        if result:
            return result

    # Step 3: Generic fallback
    return parse_with_fallback(sender, body, received_at)
