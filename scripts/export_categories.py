"""script to export current categories, sorted descending by frequency"""

import logging
import pandas as pd

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)

if __name__ == "__main__":
    logging.info("Reading the main csv file...")
    df = pd.read_csv("data/aircraft-taxonomy-db.csv")

    logging.info("Identifying and sorting categories by frequency...")
    category_sorted = (
        df["Category"].value_counts().index.to_series().reset_index(drop=True)
    )

    logging.info(f"Total Unique Categories: ({category_sorted.shape[0]}).")
    logging.info("Creating the aircraft-taxonomy-categories.csv file, sorted by frequency.")

    category_sorted.to_csv(
        "data/aircraft-taxonomy-categories.csv",
        index=False,
        header=True,
        encoding="utf8",
        lineterminator="\n",
    )

    logging.info("File created successfully!")
