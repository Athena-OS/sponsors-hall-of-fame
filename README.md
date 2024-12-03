# Sponsors List

Online at: https://athena-os.github.io/sponsors-hall-of-fame/

For manual building:

```bash
python generate.py
```

It is used by GitHub workflows to generate sponsors avatars and update the sponsor webpage.

It generates `.csv` files in `data` directory.

## GitHub Sponsors

Access to GitHub **Sponsors Dashboard** -> **Your sponsors** -> click on **Export** button and select **All time** and **CSV** file format.

You will receive an email containing the exported CSV file. Download it, rename file as `github.csv` and store it in `data` directory.

Push the changes to the repository. It will trigger GitHub workflows that update [Athena OS Sponsors Hall of Fame](https://athena-os.github.io/sponsors-hall-of-fame/) webpage.