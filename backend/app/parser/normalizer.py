import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

# Regex for Indian telecom sender prefix (e.g. VK-HDFCBK, AD-ICICIB, JM-SBICRD)
TELECOM_PREFIX_REGEX = re.compile(r"^[A-Za-z]{2}-([A-Za-z0-9_-]+)$")

def normalize_sender(sender: str) -> str:
    """
    Normalizes Indian telecom DLT sender header.
    E.g. 'VK-HDFCBK' -> 'HDFCBK', 'AD-ICICIB' -> 'ICICIB', 'BZ-SBICRD' -> 'SBICRD'.
    """
    if not sender:
        return ""
    cleaned = sender.strip()
    match = TELECOM_PREFIX_REGEX.match(cleaned)
    if match:
        cleaned = match.group(1)
    # Remove any non-alphanumeric trailing/leading characters and uppercase
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
    # Match decimal or integer number
    match = re.search(r"([0-9]+(?:\.[0-9]{1,2})?)", cleaned)
    if not match:
        return 0
    return int(Decimal(match.group(1)) * 100)

def clean_merchant(merchant: Optional[str]) -> Optional[str]:
    """
    Cleans raw merchant strings:
    - Removes prefixes like 'at', 'to', 'for', 'via', 'info:'
    - Strips trailing punctuation (., ! -)
    - Removes common payment noise words (VPA, POS, UPI txn, etc.)
    """
    if not merchant:
        return None
    
    m = merchant.strip()
    # Strip leading noise
    m = re.sub(r"^(?:at|to|for|via|info[:\s]+)\s+", "", m, flags=re.IGNORECASE)
    # Strip trailing punctuation
    m = re.sub(r"[\s\.,;!]+$", "", m)
    # Strip trailing phrases like 'on 29-09-2026' or 'Avl Lmt...' if captured
    m = re.sub(r"\s+on\s+\d{2}[-/].*$", "", m, flags=re.IGNORECASE)
    m = re.sub(r"\s+(?:Avl\s+Lmt|Available\s+Limit|Balance).*$", "", m, flags=re.IGNORECASE)
    # Normalize excessive spaces
    m = re.sub(r"\s+", " ", m).strip()
    
    return m if m else None

def parse_date(date_str: Optional[str], default_dt: Optional[datetime] = None) -> datetime:
    """
    Parses common Indian bank transaction date representations into UTC datetime.
    Falls back to default_dt or current UTC datetime if parsing fails.
    """
    if not date_str:
        return default_dt or datetime.utcnow()
    
    cleaned = date_str.strip()
    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
            
    return default_dt or datetime.utcnow()
