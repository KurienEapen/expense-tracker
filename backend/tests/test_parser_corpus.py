import pytest
from app.parser.normalizer import (
    normalize_sender,
    amount_to_paise,
    clean_merchant,
    parse_date,
)
from app.parser.registry import get_registry
from app.parser.engine import parse_message, parse_with_fallback

def test_normalize_sender():
    assert normalize_sender("VK-HDFCBK") == "HDFCBK"
    assert normalize_sender("AD-ICICIB") == "ICICIB"
    assert normalize_sender("JM-SBICRD") == "SBICRD"
    assert normalize_sender("AXISBK") == "AXISBK"
    assert normalize_sender("vm-scapia") == "SCAPIA"
    assert normalize_sender("  57575  ") == "57575"
    assert normalize_sender("") == ""

def test_amount_to_paise():
    assert amount_to_paise("1,840.00") == 184000
    assert amount_to_paise("4,500") == 450000
    assert amount_to_paise("320.50") == 32050
    assert amount_to_paise("0.75") == 75
    assert amount_to_paise(1500) == 150000
    assert amount_to_paise(45.5) == 4550
    assert amount_to_paise("invalid") == 0

def test_clean_merchant():
    assert clean_merchant("at ZOMATO.") == "ZOMATO"
    assert clean_merchant("BLUE TOKAI COFFEE.") == "BLUE TOKAI COFFEE"
    assert clean_merchant("RELIANCE DIGITAL on 29-Sep-2026") == "RELIANCE DIGITAL"
    assert clean_merchant("INDIAN OIL CORP on 29-09-2026. Surcharge waiver eligible.") == "INDIAN OIL CORP"
    assert clean_merchant(None) is None

def test_parse_date():
    dt = parse_date("29-09-2026")
    assert dt.year == 2026
    assert dt.month == 9
    assert dt.day == 29

    dt_str = parse_date("29-Sep-2026")
    assert dt_str.year == 2026
    assert dt_str.month == 9
    assert dt_str.day == 29

def test_all_yaml_corpus_test_cases():
    """
    Parametric validation of every single test case declared across all YAML files.
    Ensures 100% test coverage and accuracy of regex templates.
    """
    registry = get_registry()
    assert len(registry.templates) >= 7, "Must load at least 7 card issuer templates"

    total_tested = 0
    for template_id, compiled in registry.templates.items():
        t_def = compiled.definition
        sender = t_def.senders[0] if t_def.senders else "BANK"

        for idx, tc in enumerate(t_def.test_cases):
            parsed = parse_message(sender=sender, body=tc.input)
            assert parsed is not None, f"Template {template_id} case {idx + 1} returned None for input: {tc.input}"

            exp = tc.expected
            if exp.amount_paise is not None:
                assert parsed.amount_paise == exp.amount_paise, (
                    f"[{template_id}] Amount mismatch: expected {exp.amount_paise}, got {parsed.amount_paise}"
                )

            if exp.card_last4 is not None:
                assert parsed.card_last4 == exp.card_last4, (
                    f"[{template_id}] Card last4 mismatch: expected {exp.card_last4}, got {parsed.card_last4}"
                )

            if exp.merchant is not None:
                assert parsed.merchant_clean == exp.merchant, (
                    f"[{template_id}] Merchant mismatch: expected {exp.merchant}, got {parsed.merchant_clean}"
                )

            if exp.transaction_type is not None:
                assert parsed.transaction_type == exp.transaction_type, (
                    f"[{template_id}] Txn type mismatch: expected {exp.transaction_type}, got {parsed.transaction_type}"
                )

            if exp.category_override is not None:
                assert parsed.category == exp.category_override, (
                    f"[{template_id}] Category mismatch: expected {exp.category_override}, got {parsed.category}"
                )

            total_tested += 1

    assert total_tested >= 20, f"Expected at least 20 test cases, tested {total_tested}"

def test_fallback_parser():
    # Unknown bank SMS with amount and merchant
    body = "Rs. 750.00 debited from A/c xx9999 at STARBUCKS."
    parsed = parse_message(sender="UNKNOWNBK", body=body)
    assert parsed is not None
    assert parsed.amount_paise == 75000
    assert parsed.card_last4 == "9999"
    assert parsed.transaction_type == "debit"
    assert parsed.merchant_clean == "STARBUCKS"
    assert parsed.parser_confidence == 0.5

def test_otp_rejection():
    # Non-transactional OTP messages should NOT be parsed into transactions
    otp_body = "Your OTP for HDFC Bank NetBanking transaction is 482910. Valid for 10 minutes. Do not share."
    parsed = parse_message(sender="HDFCBK", body=otp_body)
    assert parsed is None
