import re
from typing import Dict, List, Optional

# Curated catalog of Indian merchant keywords mapped to standard categories
MERCHANT_CATEGORY_CATALOG: Dict[str, List[str]] = {
    "Food & Dining": [
        "swiggy", "zomato", "mcdonald", "kfc", "domino", "pizza", "burger",
        "starbuck", "blue tokai", "third wave", "chaayos", "chai point", "subway",
        "cafe", "restaurant", "bakery", "bake", "kitchen", "bistro", "diner",
        "dhaba", "tea", "coffee", "barbeque", "biryani", "food", "mess", "hotel",
        "plate story", "erracci", "thomsun", "namemade", "d lite", "grill",
        "rice", "palace", "culinar", "iceburg", "sweet", "shawarma", "al taza"
    ],
    "Groceries & Essentials": [
        "blinkit", "zepto", "instamart", "bigbasket", "dunzo", "bb daily",
        "nature's basket", "supermarket", "hypermarket", "mart", "grocery",
        "kirana", "provision", "spencer", "more retail", "dmart", "reliance fresh"
    ],
    "Shopping & E-Commerce": [
        "amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "tata cliq",
        "ikea", "zara", "h&m", "uniqlo", "westside", "marks & spencer",
        "decathlon", "croma", "reliance digital", "vijay sales", "parviom",
        "bata", "lenskart", "gyftr", "retail", "garments", "fashion", "optics"
    ],
    "Travel & Commute": [
        "uber", "ola", "rapido", "blusmart", "yulu", "metro", "irctc",
        "makemytrip", "cleartrip", "goibibo", "easemytrip", "indigo",
        "air india", "spicejet", "vistara", "fastag", "toll", "cochin port",
        "tyre", "tire", "auto service", "garage"
    ],
    "Fuel": [
        "indian oil", "iocl", "bharat petroleum", "bpcl", "hindustan petroleum",
        "hpcl", "shell", "fuel", "petrol", "diesel", "cng"
    ],
    "Bills & Utilities": [
        "bescom", "kseb", "tneb", "cesc", "tata power", "adani electricity",
        "jio", "airtel", "vodafone", "vi", "bsnl", "act fibernet", "tata play",
        "dishtv", "billdesk", "bbps", "electricity", "broadband", "water board"
    ],
    "Entertainment & Subscriptions": [
        "netflix", "spotify", "apple", "google play", "youtube", "hotstar",
        "disney", "prime video", "bookmyshow", "pvr", "inox", "cinepolis",
        "movie", "ticket", "cinema"
    ],
    "Health & Medical": [
        "apollo", "1mg", "tata 1mg", "pharmeasy", "netmeds", "medplus",
        "practo", "pharmacy", "chemist", "hospital", "clinic", "diagnostics"
    ],
    "Transfers & Payments": [
        "credit card payment", "payment received", "towards your", "reversal",
        "interest", "online payment", "fund transfer", "paid you", "paid to"
    ],
    "Rewards & Cashback": [
        "cashback", "reward points", "jewel", "cash back"
    ]
}

# Precompile regex with word-start boundary \b so 'starbuck' matches 'Starbucks'
COMPILED_CATALOG: Dict[str, re.Pattern] = {
    category: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")", re.IGNORECASE)
    for category, keywords in MERCHANT_CATEGORY_CATALOG.items()
}

def match_catalog_category(merchant: Optional[str]) -> Optional[str]:
    """
    Matches clean merchant name against curated keyword dictionary.
    Supports prefix root matching (e.g. 'starbuck' -> 'Starbucks').
    """
    if not merchant:
        return None
    for category, pattern in COMPILED_CATALOG.items():
        if pattern.search(merchant):
            return category
    return None
