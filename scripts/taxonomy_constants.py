"""Single source of truth for allowed taxonomy values shared across pipeline scripts."""

import re

_WS_RE = re.compile(r"\s+")


def norm_ws(value: str) -> str:
    """Collapse whitespace runs to a single space and strip the ends."""
    return _WS_RE.sub(" ", (value or "").strip())


def norm_lookup_key(value: str) -> str:
    """Casefold a raw Type/ICAO Type string for case-insensitive lookup-table matching.

    This is an in-memory search key only — never write it to disk. To produce or
    validate the canonical ``match_key`` field itself, use norm_match_key().
    """
    return norm_ws(value).casefold()


def norm_match_key(value: str) -> str:
    """Uppercase a value to produce or validate the canonical match_key field."""
    return norm_ws(value).upper()


MATCHKEY_RE = re.compile(r"^[A-Z0-9]{2,5}$")


def is_hex(value: str) -> bool:
    """Check whether a string parses as a hexadecimal integer (e.g. an ICAO code)."""
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def detect_delimiter(path) -> str:
    """Sniff whether a CSV/TSV/semicolon-separated file is comma, tab, or semicolon delimited."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(8192)
    if "\t" in sample and sample.count("\t") >= sample.count(","):
        return "\t"
    if ";" in sample and sample.count(";") > sample.count(","):
        return ";"
    return ","


# Column order for the main/custom aircraft database CSVs. Order is load-bearing:
# it's used as csv.DictWriter fieldnames when writing these files.
DB_COLUMNS = [
    "$ICAO",
    "$Registration",
    "$Operator",
    "$Type",
    "$ICAO Type",
    "#CMPG",
    "$Tag 1",
    "$#Tag 2",
    "$#Tag 3",
    "Category",
]

# Lookup-table schema: maps a match_key to its canonical taxonomy classification.
LOOKUP_COLUMNS = ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3"]

# Alias schema: maps a raw/messy type string to the match_key it resolves to.
ALIAS_COLUMNS = ["raw_value", "match_key"]


ALLOWED_CATEGORIES = {
    "AEW&C",
    "Attack / Strike",
    "Business Jet",
    "Cargo Freighter",
    "Electronic Warfare",
    "Fighter / Interceptor",
    "Helicopter - Attack",
    "Helicopter - Maritime",
    "Helicopter - Transport",
    "Helicopter - Utility",
    "ISR / Surveillance",
    "Maritime Patrol",
    "Passenger - Narrowbody",
    "Passenger - Widebody",
    "Regional Passenger",
    "Special Mission",
    "Strategic Airlift",
    "Tactical Airlift",
    "Tanker",
    "Trainer",
    "UAV - Combat",
    "UAV - Recon",
    "UAV - Utility",
    "Utility",
}

VALID_TAG1 = {
    "Tactical Transport",
    "Strategic Transport",
    "Maritime Patrol",
    "ISR",
    "Early Warning",
    "Air Superiority",
    "Strike",
    "Close Air Support",
    "Refueling",
    "Training",
    "Utility",
    "Electronic Warfare",
}

VALID_TAG2 = {
    "STOL",
    "Long Range",
    "Short Runway",
    "Heavy Lift",
    "Medium Lift",
    "Multi-Role",
    "All-Weather",
    "High Endurance",
    "Aerial Refueling",
    "Carrier Capable",
    "Amphibious",
    "Basic Trainer",
    "Light Lift",
    "Low Altitude",
}

VALID_TAG3 = {
    "Twin Turboprop",
    "Turboprop",
    "Twin Engine",
    "Quad Engine",
    "Jet",
    "High Wing",
    "Low Wing",
    "Rear Ramp",
    "Side Door",
    "Pressurized",
    "Sensor Suite",
    "Modular Cabin",
    "Single Engine",
    "Rotorcraft",
}
