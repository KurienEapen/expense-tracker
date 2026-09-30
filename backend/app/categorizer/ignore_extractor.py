import re
from typing import Tuple, Optional

CATALOG_PROMO_PATTERNS = [
    (
        r"(?i)(?:won|win|claim|get|free)\b.*?\bvoucher\b|voucher\s+code",
        "Voucher / Reward Promo"
    ),
    (
        r"(?i)pre-approved\b.*?\bloan\b|instant\s+loan|personal\s+loan.*?\bready\b",
        "Pre-approved Loan Offer"
    ),
    (
        r"(?i)credit\s+limit.*?(?:increase|enhancement|upgrade)|upgrade\s+your\s+(?:credit\s+)?card",
        "Credit Limit / Card Upgrade Promo"
    ),
    (
        r"(?i)bill\s+generated|statement\s+for\s+your|total\s+amount\s+due.*?(?:pay\s+by|due\s+date)",
        "Bill Statement Notification"
    ),
    (
        r"(?i)reward\s+points.*?(?:expir|redeem)|points\s+balance|redeem\s+now",
        "Reward Points Promo"
    ),
    (
        r"(?i)convert\s+to\s+emi|no\s+cost\s+emi|emi\s+offer|easy\s+emi",
        "EMI Conversion Offer"
    ),
    (
        r"(?i)congratulations|exclusive\s+offer|special\s+offer.*?(?:apply|click)",
        "Exclusive Promotional Offer"
    ),
]

def extract_ignore_rule_for_message(body: str, sender: Optional[str] = None) -> Tuple[str, str, Optional[str]]:
    """
    Analyzes a non-transactional SMS and automatically derives:
    1. A robust regex pattern to match future similar messages.
    2. A human-readable description for the rules manager.
    3. An optional cleaned sender filter (e.g., 'HDFCBK').
    """
    clean_sender = None
    if sender:
        # Strip DLT routing suffix (e.g., 'HDFCBK-S' -> 'HDFCBK')
        clean_sender = sender.split("-")[0].strip().upper()

    # 1. Match against catalog promo patterns
    for regex_pattern, description in CATALOG_PROMO_PATTERNS:
        if re.search(regex_pattern, body, re.IGNORECASE):
            return regex_pattern, description, clean_sender

    # 2. Fallback: Extract distinctive phrase (excluding numbers, amounts, dates, and links)
    clean_text = re.sub(r"https?://\S+", "", body)
    clean_text = re.sub(r"[\d,.]+", " ", clean_text)
    words = [w.strip() for w in clean_text.split() if len(w.strip()) > 3]

    if len(words) >= 3:
        # Use first 3 significant keywords as a pattern
        keywords = words[:3]
        pattern = r"(?i)" + ".*?".join(re.escape(k) for k in keywords)
        description = f"Non-expense alert ({' '.join(keywords[:2]).title()})"
        return pattern, description, clean_sender

    # Ultimate fallback: exact normalized snippet
    snippet = body.strip()[:60]
    pattern = r"(?i)" + re.escape(snippet)
    return pattern, "Non-transactional SMS", clean_sender
