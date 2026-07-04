"""Script that performs several tests on the main databases to see if they are still
valid CSVs.
"""

import logging
import sys

import pandas as pd

from taxonomy_constants import is_hex

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)

MAIN_DATABASE_NAME = "data/aircraft-taxonomy-db.csv"


def contains_duplicate_ICAOs(df) -> list[str]:
    """Return a violation message if the database has any duplicate ICAO codes.

    Args:
        df (pandas.Dataframe): The database to check.
    """
    duplicate_icao = df[df.duplicated(subset="$ICAO", keep=False)]["$ICAO"]
    if len(duplicate_icao) == 0:
        return []
    return [
        f"has {duplicate_icao.shape[0]} duplicate ICAO codes:\n"
        f"{duplicate_icao.to_string(index=False)}"
    ]


def contains_duplicate_regs(df) -> list[str]:
    """Return a violation message if the database has any duplicate registration numbers.

    Not run by default: registration numbers are legitimately reused across
    operators (military serial-number blocks, "????" placeholders for unknown
    registrations, etc.), so duplicates here are not necessarily errors. Call
    this explicitly if you want to inspect them.

    Args:
        df (pandas.Dataframe): The database to check.
    """
    duplicate_regs = df[df.duplicated(subset="$Registration", keep=False)][
        ["$ICAO", "$Registration"]
    ]
    if len(duplicate_regs) == 0:
        return []
    return [
        f"has {duplicate_regs.shape[0]} duplicate registration numbers:\n"
        f"{duplicate_regs.to_string(index=False)}"
    ]


def contains_valid_ICAO_hexes(df) -> list[str]:
    """Return a violation message if any '$ICAO' value is not a hexadecimal string.

    Args:
        df (pandas.Dataframe): The database to check.
    """
    invalid_hexes = df[~df["$ICAO"].apply(is_hex).astype(bool)]["$ICAO"]
    if len(invalid_hexes) == 0:
        return []
    noun = "value" if invalid_hexes.shape[0] == 1 else "values"
    verb = "is" if invalid_hexes.shape[0] == 1 else "are"
    return [
        f"has {invalid_hexes.shape[0]} '$ICAO' {noun} that {verb} not hexadecimal:\n"
        f"{invalid_hexes.to_string(index=False)}"
    ]


def main() -> int:
    logging.info("Checking the main database...")
    try:
        main_df = pd.read_csv(MAIN_DATABASE_NAME)
    except Exception as exc:
        logging.error("The '%s' database is not a valid CSV.", MAIN_DATABASE_NAME)
        sys.stdout.write(f"The '{MAIN_DATABASE_NAME}' database is not a valid CSV: {exc}\n")
        return 1

    violations = contains_duplicate_ICAOs(main_df) + contains_valid_ICAO_hexes(main_df)
    # contains_duplicate_regs() is intentionally not run here - see its docstring.

    if violations:
        for violation in violations:
            message = f"The '{MAIN_DATABASE_NAME}' database {violation}"
            logging.error(message)
            sys.stdout.write(message + "\n")
        return 1

    logging.info("The main database is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
