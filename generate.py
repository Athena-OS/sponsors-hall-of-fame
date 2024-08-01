import base64
from io import BytesIO
import math
import sys
import pandas as pd
import os
import argparse

import requests
from PIL import Image
from PIL import ImageDraw

# Set display options
pd.set_option('display.max_rows', None)

# Create table mapping tier images to donation amounts.
tiers = pd.DataFrame([
    {"Tier": "tier0", "Min": 0},
    {"Tier": "tier1", "Min": 2},
    {"Tier": "tier2", "Min": 5},
    {"Tier": "tier3", "Min": 10},
    {"Tier": "tier4", "Min": 20},
    {"Tier": "tier5", "Min": 50},
    {"Tier": "tier6", "Min": 100},
    {"Tier": "tier7", "Min": 200},
    {"Tier": "tier8", "Min": 500},
    {"Tier": "tier9", "Min": 1000},
    {"Tier": "tier10", "Min": 2000},
    {"Tier": "tier11", "Min": 5000}
])


def createAvatarImage(avatar_url, amount, size):
    if avatar_url.startswith("http"):
        response = requests.get(avatar_url, headers={
                                "User-Agent": "Mozilla/5.0"})
        image = Image.open(BytesIO(response.content))
    else:
        image = Image.open(avatar_url)

    avatar_size = math.floor(size * 64.0 / 135.0)

    image = image.resize((avatar_size, avatar_size))
    image = image.convert('RGBA')

    # Crop the image to a circle.
    mask = Image.new('L', (avatar_size, avatar_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    image = Image.composite(image, Image.new(
        'RGBA', (avatar_size, avatar_size), (0, 0, 0, 0)), mask)

    # Add padding to the image.
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    padding = int((size - avatar_size) / 2)
    canvas.paste(image, (padding, padding))

    # Choose and load tier image.
    tier = tiers[tiers["Min"] <= amount].iloc[-1]
    tier_image = Image.open("img/{}.png".format(tier["Tier"]))
    tier_image = tier_image.resize((size, size))

    # Add tier image to avatar.
    canvas = Image.alpha_composite(canvas, tier_image)

    # Convert the image to a base64 string.
    buffered = BytesIO()
    canvas.save(buffered, format="PNG")

    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def ellipsize(name, max_length):
    return (name[:max_length-1] + '…') if len(name) > max_length else name


def getGitHubSponsors():
    # Return empty DataFrame if data/github.csv does not exist.
    if not os.path.isfile("data/github.csv"):
        return pd.DataFrame()

    # Read the CSV file.
    sponsors = pd.read_csv("data/github.csv")

    # Remove all private sponsorships.
    sponsors = sponsors[sponsors["Is Public?"] == True]

    # Only keep required columns.
    sponsors = sponsors[["Sponsor Handle",
                         "Sponsor Profile Name", "Processed Amount"]]

    # Add a "Link" column.
    sponsors = sponsors.assign(
        Link="https://github.com/" + sponsors["Sponsor Handle"])

    # Add a "Avatar" column.
    sponsors = sponsors.assign(
        Avatar=sponsors["Link"] + ".png?size=64")

    # Create a new "Name" column which is "Sponsor Profile Name" if it exists, otherwise "Sponsor Handle".
    sponsors = sponsors.assign(
        Name=sponsors["Sponsor Profile Name"].fillna(sponsors["Sponsor Handle"]))

    # Only keep required columns.
    sponsors = sponsors[["Name", "Processed Amount", "Link", "Avatar"]]

    # Parse the "Processed Amount" column as numbers (stripping the leading $).
    sponsors["Processed Amount"] = sponsors["Processed Amount"].str[1:].astype(
        float)

    # Group by "Name" and sum the "Processed Amount" column.
    sponsors = sponsors.groupby(["Name", "Link", "Avatar"]).sum()

    # Rename the "Processed Amount" column to "Total".
    sponsors = sponsors.rename(columns={"Processed Amount": "Total"})

    sponsors = sponsors.reset_index()

    return sponsors


def getGitHubAmountSince(date):
    if not os.path.isfile("data/github.csv"):
        return 0.0

    # Read the CSV file.
    sponsors = pd.read_csv("data/github.csv")

    # Only keep required columns.
    sponsors = sponsors[["Transaction Date", "Processed Amount"]]

    # Parse the "Processed Amount" column as numbers (stripping the leading $).
    sponsors["Processed Amount"] = sponsors["Processed Amount"].str[1:].astype(
        float)

    # Sum the "Processed Amount" column for all rows where the date is after the given date.
    sponsors["Transaction Date"] = pd.to_datetime(
        sponsors["Transaction Date"], utc=True).dt.date

    total = sponsors[sponsors["Transaction Date"] >
                     date.date()]["Processed Amount"].sum()

    return total


def getKofiSponsors():

    # Return empty DataFrame if data/ko-fi.csv does not exist.
    if not os.path.isfile("data/ko-fi.csv"):
        return pd.DataFrame()

    # Read the CSV file.
    sponsors = pd.read_csv("data/ko-fi.csv")

    # Remove all rows where the name is "Ko-fi Supporter".
    sponsors = sponsors[sponsors["From"] != "Ko-fi Supporter"]

    # Only keep name and amount columns.
    sponsors = sponsors[["From", "Received"]]

    # Strip my own donations.
    sponsors = sponsors[sponsors["From"] != "Simon Schneegans"]

    # Group by "Name" and sum the "Processed Amount" column.
    sponsors = sponsors.groupby(["From"]).sum()

    # Rename the "Processed Amount" column to "Total".
    sponsors = sponsors.rename(columns={"Received": "Total"})

    # Rename the index column to "Name".
    sponsors = sponsors.rename_axis("Name")

    # Add link and avatar columns.
    meta = pd.read_csv("data/ko-fi-meta.csv")
    meta = meta.set_index("Name")
    sponsors = sponsors.join(meta)

    sponsors = sponsors.reset_index()

    return sponsors


def getKofiAmountSince(date):

    if not os.path.isfile("data/ko-fi.csv"):
        return 0.0

    # Read the CSV file.
    sponsors = pd.read_csv("data/ko-fi.csv")

    # Strip my own donations.
    sponsors = sponsors[sponsors["From"] != "Simon Schneegans"]

    # Only keep amount and date columns.
    sponsors = sponsors[["Received", "DateTime (UTC)"]]

    # Sum the "Received" column for all rows where the date is after the given date.
    sponsors["DateTime (UTC)"] = pd.to_datetime(
        sponsors["DateTime (UTC)"], utc=True).dt.date

    total = sponsors[sponsors["DateTime (UTC)"] >
                     date.date()]["Received"].sum()

    return total


def getPaypalSponsors():

    # Return empty DataFrame if data/paypal.csv does not exist.
    if not os.path.isfile("data/paypal.csv"):
        return pd.DataFrame()

    # Read the CSV file.
    sponsors = pd.read_csv("data/paypal.csv")

    # Remove all private sponsorships.
    sponsors = sponsors[sponsors["Public"] == True]

    # Only keep amount and date columns.
    sponsors = sponsors[["Name", "Link", "Avatar", "Total"]]

    return sponsors


def getPaypalAmountSince(date):
    if not os.path.isfile("data/paypal.csv"):
        return 0.0

    # Read the CSV file.
    sponsors = pd.read_csv("data/paypal.csv")

    # Only keep amount and date columns.
    sponsors = sponsors[["Total", "Date"]]

    # Sum the "Total" column for all rows where the date is after the given date.
    sponsors["Date"] = pd.to_datetime(
        sponsors["Date"], utc=True).dt.date

    total = sponsors[sponsors["Date"] >
                     date.date()]["Total"].sum()

    return total


def writeAvatarGrid(sponsors, top_offset, image_width, columns, avatar_size, x_gap, y_gap, max_name_length):
    svg = ""

    for i in range(len(sponsors)):
        sponsor = sponsors.iloc[i]

        print("{} ${}".format(sponsor["Name"], sponsor["Total"]))

        # Start avatar-enclosing link.
        if not pd.isnull(sponsor["Link"]):
            svg += '<a href="{}" target="_blank">\n'.format(sponsor["Link"])

        # Compute the number of sponsors on the current row. If this is last row, it may have fewer
        # sponsors. In this case, we need to add some margin to center the avatars.
        row = i // columns
        items_in_row = min(len(sponsors) - row * columns, columns)
        padding = (image_width - (items_in_row * avatar_size + (items_in_row - 1) * x_gap)) / 2

        # Compute the x and y position of the sponsor.
        x = (i % columns) * (avatar_size + x_gap) + padding
        y = (i // columns) * (avatar_size + y_gap) + top_offset

        # Write the sponsor's avatar.
        avatar = createAvatarImage(sponsor["Avatar"], sponsor["Total"], avatar_size)
        svg += '<image x="{}px" y="{}px" width="{}px" height="{}px" href="data:image/jpeg;charset=utf-8;base64,{}" />\n'.format(
            x, y, avatar_size, avatar_size, avatar)

        # Write the sponsor's name.
        if max_name_length > 0:
            name = ellipsize(sponsor["Name"], max_name_length)
            svg += '<text x="{}px" y="{}px" text-anchor="middle">{}</text>\n'.format(
                x + avatar_size/2, y + avatar_size + 5, name)

        # Close avatar-enclosing link.
        if not pd.isnull(sponsor["Link"]):
            svg += '</a>\n'

    return svg


def writeTinySVG(sponsors, file_name):
    avatar_size = 48
    x_gap = 4
    y_gap = 0
    columns = 16
    max_name_length = 0

    # Compute the total width and height of the image.
    width = 830
    height = (math.ceil(len(sponsors) / columns)) * (avatar_size + y_gap)

    avatars = writeAvatarGrid(sponsors, 0, width, columns, avatar_size, x_gap, y_gap, max_name_length)

    svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="{}px" height="{}px">
            {}
        </svg>
    '''.format(width, height, avatars)

    with open(file_name, "w") as f:
        f.write(svg)


def writeSmallSVG(sponsors, file_name, dark):
    avatar_size = 115
    x_gap = 4
    y_gap = 10
    columns = 7
    max_name_length = 16

    # Compute the total width and height of the image.
    width = 830
    height = (math.ceil(len(sponsors) / columns)) * (avatar_size + y_gap)

    avatars = writeAvatarGrid(sponsors, 0, width, columns, avatar_size, x_gap, y_gap, max_name_length)

    svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="{}px" height="{}px">
            <style>
                text {{
                    font-family: sans-serif;
                    font-weight: bold;
                    font-size: 9pt;
                    fill: {}
                }}
                a:hover text {{
                    text-decoration: underline;
                }}
            </style>
            {}
        </svg>
    '''.format(width, height, "white" if dark else "black", avatars)

    with open(file_name, "w") as f:
        f.write(svg)


def writeLargeSVG(sponsors, file_name, dark):
    avatar_sizes = [130, 130, 130, 160, 160, 160, 190, 190, 190, 210, 210, 210]
    columns = [6, 6, 6, 5, 5, 5, 4, 4, 4, 3, 3, 3]
    max_name_length = [14, 14, 14, 16, 16, 16, 18, 18, 18, 20, 20, 20]
    tier_names = ["👍 Entry Level", "Coffee Level ☕", "🍕 Pizza Level", "🥉 Bronze Level 🥉", "🥈 Silver Level 🥈",
                  "🥇 Gold Level 🥇", "❤️ Awesome Supporters ❤️", "💖 Very Awesome Supporters 💖",
                  "❤️‍🔥 Fiercely Awesome Supporters ❤️‍🔥", "✨ Unbelievably Awesome Supporters ✨",
                  "🌟 Truly Unbelievably Awesome Supporters 🌟", "🚀 The Best 🚀"]
    x_gap = 4
    y_gap = 10
    tier_gap = 120

    # Group sponsors by tier and Reverse the order.
    groups = sponsors.groupby(pd.cut(sponsors["Total"], tiers["Min"], right=False))
    groups = list(groups)[::-1]

    # We will compute the total height of the image as we go.
    width = 830
    height = 0

    avatars = ""

    # Iterate over all sponsors groups.
    for tier_range, group in groups:
        if group.empty:
            continue

        # Write the tier heading.
        height += tier_gap
        tier_amount = tier_range.left
        tier = tiers[tiers["Min"] == tier_amount].iloc[0].name
        avatars += '<text class="heading" x="{}px" y="{}px" text-anchor="middle">{}</text>\n'.format(
            width / 2, height - 20, tier_names[tier])

        if tier_amount > 0:
            avatars += '<text class="subheading" x="{}px" y="{}px" text-anchor="middle">${}+</text>\n'.format(
                width / 2, height, tier_amount)

        avatars += writeAvatarGrid(group, height, width, columns[tier],
                                   avatar_sizes[tier],
                                   x_gap, y_gap, max_name_length[tier])

        rows = math.ceil(len(group) / columns[tier])
        height += rows * (avatar_sizes[tier] + y_gap)

    height += tier_gap / 2

    svg = '''
        <svg xmlns="http://www.w3.org/2000/svg" width="{}px" height="{}px">
            <style>
                text {{
                    font-family: sans-serif;
                    font-weight: bold;
                    font-size: 11pt;
                    fill: {}
                }}
                text.heading {{
                    font-weight: 300;
                    font-size: 20pt;
                }}
                text.subheading {{
                    font-weight: normal;
                    font-size: 11pt;
                    fill: gray;
                }}
                a:hover text {{
                    text-decoration: underline;
                }}
            </style>
            {}
        </svg>
    '''.format(width, height, "white" if dark else "black", avatars)

    with open(file_name, "w") as f:
        f.write(svg)


def mergeDuplicates(sponsors):
    synonyms = {
        "DonHopkins": "Don Hopkins",
        "AJCxZ0": "Andrew J. Caines",
        "DR_TS": "denis-roy",
        "James Vega": "D3vil0p3r",
        "markpieheart": "JonathanHolt"
    }

    # Replace synonyms.
    for synonym, name in synonyms.items():
        sponsors.loc[sponsors["Name"] == synonym, "Name"] = name

    # Merge duplicate sponsors.
    sponsors = sponsors.groupby("Name").agg(
        {"Total": "sum", "Link": "first", "Avatar": "first"})

    return sponsors


def getAmountSince(date):
    kofi = getKofiAmountSince(date)
    github = getGitHubAmountSince(date)
    paypal = getPaypalAmountSince(date)
    total = kofi + github + paypal
    return math.floor(total)


if __name__ == "__main__":

    # Parse the command line arguments.

    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", action="store_true")
    parser.add_argument("--weekly", action="store_true")
    parser.add_argument("--total", action="store_true")
    parser.add_argument("--graph", action="store_true")
    parser.add_argument("--donors", action="store_true")
    parser.add_argument("--platforms", action="store_true")
    args = parser.parse_args()

    # ---------------------------------------------------------------------------------- #
    # ------------------------------- Create the SVG ----------------------------------- #
    # ---------------------------------------------------------------------------------- #

    if args.svg:

        # Get the sponsors from GitHub, Ko-fi and PayPal.
        github = getGitHubSponsors()
        kofi = getKofiSponsors()
        paypal = getPaypalSponsors()

        # Concatenate the two DataFrames.
        # sponsors = pd.concat([paypal])
        sponsors = pd.concat([github, kofi, paypal])

        # Merge duplicate sponsors.
        sponsors = mergeDuplicates(sponsors)

        # Sort by "Total" column.
        sponsors = sponsors.sort_values(by=["Total"], ascending=False)
        sponsors = sponsors.reset_index()

        print("\nGenerated big light SVG\n")
        writeLargeSVG(sponsors, "www/sponsors_light_big.svg", dark=False)

        print("\nGenerated big dark theme SVG\n")
        writeLargeSVG(sponsors, "www/sponsors_dark_big.svg", dark=True)

        print("\nGenerated small light SVG\n")
        writeSmallSVG(sponsors, "www/sponsors_light_small.svg", dark=False)

        print("\nGenerated small dark SVG\n")
        writeSmallSVG(sponsors, "www/sponsors_dark_small.svg", dark=True)

        print("\nGenerated tiny SVG\n")
        writeTinySVG(sponsors, "www/sponsors_tiny.svg")

    # ---------------------------------------------------------------------------------- #
    # -------------------- Print a graph showing the monthly income -------------------- #
    # ---------------------------------------------------------------------------------- #

    if args.graph:

        # Create a DataFrame with a row for each month since 2019-01-01.
        start = pd.Timestamp(2021, 1, 1)
        months = pd.date_range(
            start=start, end=pd.Timestamp.now(), freq="MS")
        months = pd.DataFrame(months, columns=["Date"])

        total = getAmountSince(start)

        # Add a "Amount Since Start" column.
        months = months.assign(
            TotalAmount=months["Date"].apply(lambda x: total - getAmountSince(x)))

        # Add a "Amount This Month" column by computing the difference between the
        # current and previous month. Convert the column to integers.
        months = months.assign(Amount=months["TotalAmount"].diff().fillna(0))
        months["Amount"] = months["Amount"].astype(int)

        months.to_csv(sys.stdout, index=False)

    # ---------------------------------------------------------------------------------- #
    # ------------------------------- Print the donors --------------------------------- #
    # ---------------------------------------------------------------------------------- #

    if args.donors:

        # Get the sponsors from GitHub, Ko-fi and PayPal.
        github = getGitHubSponsors()
        kofi = getKofiSponsors()
        paypal = getPaypalSponsors()

        # Concatenate the two DataFrames.
        sponsors = pd.concat([github, kofi, paypal])

        # Merge duplicate sponsors.
        sponsors = mergeDuplicates(sponsors)

        # Remove Link and Avatar columns.
        sponsors = sponsors.drop(columns=["Link", "Avatar"])

        # Sort by "Total" column.
        sponsors = sponsors.sort_values(by=["Total"], ascending=False)
        sponsors = sponsors.reset_index()

        sponsors.to_csv(sys.stdout, index=False)

    # ---------------------------------------------------------------------------------- #
    # ------------------------------- Print the platforms ------------------------------ #
    # ---------------------------------------------------------------------------------- #

    if args.platforms:

        # Get the sponsors from GitHub, Ko-fi and PayPal.
        github = getGitHubSponsors()
        kofi = getKofiSponsors()
        paypal = getPaypalSponsors()

        # Create a DataFrame with the totals.
        platforms = pd.DataFrame([
            {"Platform": "GitHub", "Total": github["Total"].sum().astype(int)},
            {"Platform": "Ko-fi", "Total": kofi["Total"].sum().astype(int)},
            {"Platform": "PayPal", "Total": paypal["Total"].sum().astype(int)}
        ])

        platforms.to_csv(sys.stdout, index=False)

    # ---------------------------------------------------------------------------------- #
    # ----------- Get the amount of money raised in the last couple of weeks ----------- #
    # ---------------------------------------------------------------------------------- #

    if args.weekly:
        weeks = 53
        date = pd.Timestamp.now() - pd.Timedelta(weeks=weeks)
        print(math.floor(getAmountSince(date) / weeks))

    # ---------------------------------------------------------------------------------- #
    # ------------ Get the amount of money raised since the dawn of time --------------- #
    # ---------------------------------------------------------------------------------- #

    if args.total:
        print(getAmountSince(pd.Timestamp(2000, 1, 1)))
