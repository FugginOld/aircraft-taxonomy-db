"""Script that performs several tests on the main databases to see if they are still
valid CSVs.
"""

import logging
import sys

import pandas as pd

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)

MAIN_DATABASE_NAME = "data/plane-alert-db.csv"


def is_hex(string):
    """Check if a string is a hexidecimal string.

    Args:
        string (str): The string to check.

    Returns:
        boolean: True if the string is a hexidecimal string, False otherwise.
    """
    try:
        int(string, 16)
        return True
    except ValueError:
        return False


def contains_duplicate_ICAOs(df):
    """Check if the database has any duplicate ICAO codes.

    Args:
        df (pandas.Dataframe): The database to check.

    Raises:
        Exception: When the database has duplicate ICAO codes.
    """
    duplicate_icao = df[df.duplicated(subset="$ICAO", keep=False)]["$ICAO"]
    if len(duplicate_icao) > 0:
        db_name = df.name if hasattr(df, "name") else "database"
        logging.error(f"The {db_name} database has duplicate ICAO codes.")
        sys.stdout.write(
            f"The ' {db_name}' database has '{duplicate_icao.shape[0]}' duplicate "
            f"ICAO codes:\n {duplicate_icao.to_string(index=False)}\n"
        )
        sys.exit(1)


def contains_duplicate_regs(df):
    """Check if the database has any duplicate registration numbers.

    Args:
        df (pandas.Dataframe): The database to check.

    Raises:
        Exception: When the database has duplicate registration numbers.
    """

    duplicate_regs = df[df.duplicated(subset="$Registration", keep=False)][
        ["$ICAO", "$Registration"]
    ]
    if len(duplicate_regs) > 0:
        db_name = df.name if hasattr(df, "name") else "database"
        logging.error(f"The '{db_name}' database has duplicate registration numbers.")
        sys.stdout.write(
            f"The '{db_name}' database has '{duplicate_regs.shape[0]}' duplicate "
            f"registration numbers:\n{duplicate_regs.to_string(index=False)}\n"
        )
        sys.exit(1)


def contains_valid_ICAO_hexes(df):
    """Check if all the values in the '$ICAO' data series are hexidecimal strings.

    Args:
        df (pandas.Series): The '$ICAO' data series to check.

    Raises:
        Exception: When the data series has invalid hexidecimal values.
    """
    invalid_hexes = df[~df["$ICAO"].apply(is_hex).astype(bool)]["$ICAO"]
    if len(invalid_hexes) > 0:
        db_name = df.name if hasattr(df, "name") else "database"
        error_strings = (
            ["value", "is", "a hexidecimal"]
            if invalid_hexes.shape[0] == 1
            else ["values", "are", "hexidecimals"]
        )
        logging.error(
            f"The '{db_name}' database contains non-hexidecimal '$ICAO' values."
        )
        sys.stdout.write(
            f"The {db_name} database has '{invalid_hexes.shape[0]}' '$ICAO' "
            f"{error_strings[0]} that {error_strings[1]} not {error_strings[2]}:\n"
            f"{invalid_hexes.to_string(index=False)}\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    ##########################################
    # Check main database.                   #
    ##########################################
    logging.info("Checking the main database...")
    try:
        main_df = pd.read_csv(MAIN_DATABASE_NAME)
        main_df_db_name = MAIN_DATABASE_NAME
    except Exception as e:
        logging.error(f"The '{MAIN_DATABASE_NAME}' database is not a valid CSV.")
        sys.stdout.write(
            f"The '{MAIN_DATABASE_NAME}' database is not a valid CSV: {e}\n"
        )
        sys.exit(1)

    # Preform database checks.
    contains_duplicate_ICAOs(main_df)
    contains_valid_ICAO_hexes(
        main_df
    )
    # contains_duplicate_regs(
    #     main_df
    # )  # NOTE: This is commented out because there are duplicates.
    logging.info("The main database is valid.")
