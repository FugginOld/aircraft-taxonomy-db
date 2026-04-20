# Read before making changes

Please only suggest/make any changes to the following files:

- [aircraft-taxonomy-db.csv](data/aircraft-taxonomy-db.csv): A list of interesting aircraft with tags, categories and links.
- [aircraft-taxonomy-pia.csv](data/aircraft-taxonomy-pia.csv): A list that contains PIA planes.

All other files are generated from this file using the [.github/workflows/create_db_derivatives.yaml](.github/workflows/create_db_derivatives.yaml) GitHub action, and if you do not make your changes there, they will be overwritten and lost.

Note: As Twitter has almost entirely withdrawn API support for free users, we no longer create a separate CSV for use with Twitter bots.
