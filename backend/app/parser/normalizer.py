import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

# Regex for Indian telecom sender prefix (e.g. VK-HDFCBK, AD-ICICIB, JM-SBICRD)
TELECOM_PREFIX_REGEX = re.compile(r"^[A-Za-z]{2}-([A-Za-z0-9_-]+)$")
# Suffix for TRAI DLT communication types (e.g. -S for Service, -T for Transactional, -P for Promotional)
DLT_SUFFIX_REGEX = re.compile(r"[-_]([STPG])$", re.IGNORECASE)

KNOWN_PACKAGE_SENDERS = {
    "com.google.android.apps.nbu.paisa.user": "GPAY",
    "com.phonepe.app": "PHONEPE",
    "net.one97.paytm": "PAYTM",
}

def normalize_sender(sender: str) -> str:
    """
    Normalizes Indian telecom DLT sender headers and Android app packages.
    E.g. 'VK-HDFCBK-S' -> 'HDFCBK', 'HSBCIN-S' -> 'HSBCIN', 'AXISBK-S' -> 'AXISBK',
    'com.google.android.apps.nbu.paisa.user' -> 'GPAY'.
    """
    if not sender:
        return ""
    cleaned = sender.strip()

    if cleaned in KNOWN_PACKAGE_SENDERS:
        return KNOWN_PACKAGE_SENDERS[cleaned]

    # Strip telecom circle prefix (e.g. VK-, AD-)
    match = TELECOM_PREFIX_REGEX.match(cleaned)
    if match:
        cleaned = match.group(1)

    # Strip TRAI route suffix (e.g. -S, -T, -P, -G)
    cleaned = DLT_SUFFIX_REGEX.sub("", cleaned)

    # Remove any remaining non-alphanumeric characters and uppercase
    cleaned = re.sub(r"[^A-Za-z0-9]", "", cleaned)
    return cleaned.upper()

def amount_to_paise(amt: Union[str, float, int, Decimal]) -> int:
    """
    Converts amount string/number to integer paise (1 INR = 100 paise).
    Handles '1,840.00' -> 184000, '4,500' -> 450000, '0.50' -> 50.
    """
    if amt is None:
        return 0
    if isinstance(amt, (int, float, Decimal)):
        return int(round(float(amt) * 100))
    
    cleaned = str(amt).replace(",", "").strip()
    match = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", cleaned)
    if not match:
        return 0
    return int(Decimal(match.group(1)) * 100)

def clean_merchant(merchant: Optional[str]) -> Optional[str]:
    """
    Cleans raw merchant strings:
    - Removes gateway prefixes like 'raz*', 'payu*', 'billdesk*'
    - Strips leading noise like 'at', 'to', 'for', 'via', 'info:'
    - Cleans e-commerce noise (e.g. 'amazonin' -> 'Amazon', 'online order' suffix)
    - Strips trailing punctuation (., ! -)
    """
    if not merchant:
        return None
    
    m = merchant.strip()

    # Strip gateway prefixes like raz* or payu*
    m = re.sub(r"^(?:raz\*|payu\*|billdesk\*|ccavenue\*|paytm\*)\s*", "", m, flags=re.IGNORECASE)

    # Strip leading noise
    m = re.sub(r"^(?:at|to|for|via|info[:\s]+)\s+", "", m, flags=re.IGNORECASE)

    # Strip trailing phrases
    m = re.sub(r"\s+online\s+order.*$", "", m, flags=re.IGNORECASE)
    m = re.sub(r"\s+on\s+\d{2}[-/].*$", "", m, flags=re.IGNORECASE)
    m = re.sub(r"\s+(?:Avl\s+Lmt|Available\s+Limit|Balance|Limit\s+Rs|Due\s+Rs|Report\s+fraud).*$", "", m, flags=re.IGNORECASE)

    # Clean known merchant spellings
    m_lower = m.lower().strip()
    if m_lower in ("amazonin", "amazon in", "amazon pay"):
        return "Amazon"
    if m_lower in ("swiggy", "swiggy in", "swiggy instamart"):
        return "Swiggy"
    if m_lower in ("zomato", "zomato in"):
        return "Zomato"

    # Strip trailing punctuation
    m = re.sub(r"[\s\.,;!]+$", "", m)
    # Normalize excessive spaces
    m = re.sub(r"\s+", " ", m).strip()

    # If all-caps and >3 chars without embedded digits, make title-cased for readability
    if m.isupper() and len(m) > 3 and not re.search(r"\d", m):
        m = m.title()

    return m if m else None

def parse_date(date_str: Optional[str], default_dt: Optional[datetime] = None) -> datetime:
    """
    Parses bank transaction date representations into UTC datetime.
    Supports Indian formats, 2-digit years, and timestamps.
    """
    if not date_str:
        return default_dt or datetime.utcnow()
    
    cleaned = date_str.strip()
    # Strip trailing timezone tags like 'IST'
    cleaned = re.sub(r"\s+IST$", "", cleaned, flags=re.IGNORECASE)

    formats = [
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%y %H:%M:%S",
        "%Y-%m-%d:%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d/%b/%Y",
        "%d/%b/%y",
        "%d %b %Y",
        "%d %b %y",
        "%d-%B-%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
            
    return default_dt or datetime.utcnow()
