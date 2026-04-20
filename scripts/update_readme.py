"""Script that performs several counts to update the README"""

import logging
import pandas as pd
import chevron

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)

if __name__ == "__main__":
    logging.info("Reading the main csv file...")
    df = pd.read_csv("data/aircraft-taxonomy-db.csv")

    logging.info("Reading the PIA csv file...")
    pia_df = pd.read_csv("data/aircraft-taxonomy-pia.csv")
    logging.info("All csv files read successfully.")

    plane_count_df = df["$ICAO"].drop_duplicates().reset_index(drop=True)
    logging.info(f"Total Planes Count: ({plane_count_df.shape[0]}).")

    category_unique_df = df["Category"].drop_duplicates().reset_index(drop=True)
    logging.info(f"Total Categories Count: ({category_unique_df.shape[0]}).")

    logging.info("Generating Counts to update README.md via mustache template.")

    with open("readme.mustache", "r") as template:
        with open("README.md", "w") as output:
            output.write(
                chevron.render(
                    template,
                    {
                        "planes": plane_count_df.shape[0],
                        "categories": category_unique_df.shape[0],
                        "plane_alert_db": df.shape[0],
                        "plane_alert_pia": pia_df.shape[0],
                        "civ_count": df[df["#CMPG"] == "Civ"].shape[0],
                        "mil_count": df[df["#CMPG"] == "Mil"].shape[0],
                        "pol_count": df[df["#CMPG"] == "Pol"].shape[0],
                        "gov_count": df[df["#CMPG"] == "Gov"].shape[0],
                    },
                )
            )
        logging.info("Counts output to README.md via 'readme.mustache' template.")
