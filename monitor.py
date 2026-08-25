import json
import os
import re
import urllib.request
from playwright.sync_api import sync_playwright

WOONSTAD_URL = "https://www.woonstadrotterdam.nl/aanbod/vrije-sector-huurwoning"
STATE_FILE = "state.json"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_URL = "https://ntfy.sh/" + NTFY_TOPIC


def get_listings():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130 Safari/537.36"
            )
        )

        print("Opening Woonstad...")

        page.goto(
            WOONSTAD_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # Give the Woonstad application time to load the properties.
        page.wait_for_timeout(10000)

        links = page.locator(
            'a[href*="/aanbod/vrije-sector-huurwoning/"]'
        ).all()

        listings = set()

        for link in links:

            href = link.get_attribute("href")

            if not href:
                continue

            if href.startswith("/"):
                href = "https://www.woonstadrotterdam.nl" + href

            if "/aanbod/vrije-sector-huurwoning/" in href:
                listings.add(href.split("?")[0])

        browser.close()

        return sorted(listings)


def load_previous():

    if not os.path.exists(STATE_FILE):
        return []

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_current(listings):

    with open(STATE_FILE, "w") as f:
        json.dump(listings, f, indent=2)


def notify(new_listings):

    if not new_listings:
        return

    message = (
        "🏠 NIEUWE WOONSTAD WONING!\n\n"
        + "\n\n".join(new_listings[:10])
    )

    request = urllib.request.Request(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": "Nieuwe Woonstad woning!",
            "Priority": "max",
            "Tags": "house",
            "Click": new_listings[0],
        },
        method="POST",
    )

    urllib.request.urlopen(request, timeout=30)


def main():

    print("Checking Woonstad...")

    current = get_listings()

    print("Listings found:", len(current))

    previous = load_previous()

    if not previous:

        save_current(current)

        print("First run completed.")
        print("Current listings saved as baseline.")

        return

    new = [
        listing
        for listing in current
        if listing not in previous
    ]

    print("New listings:", len(new))

    if new:

        for listing in new:
            print("NEW:", listing)

        notify(new)

    else:
        print("No new listings.")

    save_current(current)


if __name__ == "__main__":
    main()
