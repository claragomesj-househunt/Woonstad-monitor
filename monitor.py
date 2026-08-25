import json
import os
import urllib.request
from html.parser import HTMLParser

WOONSTAD_URL = "https://www.woonstadrotterdam.nl/aanbod/vrije-sector-huurwoning"
STATE_FILE = "state.json"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_URL = "https://ntfy.sh/" + NTFY_TOPIC


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        attrs = dict(attrs)
        href = attrs.get("href", "")

        if href:
            self.links.append(href)


def get_page():
    request = urllib.request.Request(
        WOONSTAD_URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def get_listings(html):
    parser = LinkParser()
    parser.feed(html)

    listings = set()

    for href in parser.links:

        # Woonstad property URLs look like:
        # /aanbod/vrije-sector-huurwoning/PROPERTY-ID-address
        if href.startswith("/aanbod/vrije-sector-huurwoning/"):
            full_url = "https://www.woonstadrotterdam.nl" + href
            listings.add(full_url)

        elif href.startswith(
            "https://www.woonstadrotterdam.nl/aanbod/vrije-sector-huurwoning/"
        ):
            listings.add(href)

    return sorted(listings)


def load_previous():
    if not os.path.exists(STATE_FILE):
        return []

    try:
        with open(STATE_FILE, "r") as file:
            return json.load(file)
    except Exception:
        return []


def save_current(listings):
    with open(STATE_FILE, "w") as file:
        json.dump(listings, file, indent=2)


def send_notification(new_listings):
    if not new_listings:
        return

    message = (
        "🏠 NIEUWE WOONSTAD WONING!\n\n"
        + "\n\n".join(new_listings)
    )

    request = urllib.request.Request(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": "Nieuwe Woonstad woning!",
            "Priority": "max",
            "Tags": "house",
            "Click": new_listings[0]
        },
        method="POST"
    )

    urllib.request.urlopen(request, timeout=30)


def main():

    print("Checking Woonstad...")

    html = get_page()
    current_listings = get_listings(html)
    previous_listings = load_previous()

    print("Listings found:", len(current_listings))

    # FIRST RUN:
    # Save the current listings but don't send notifications.
    if not previous_listings:
        save_current(current_listings)

        print("First run completed.")
        print("Current listings saved as baseline.")
        return

    # Find listings that weren't there during the previous check.
    new_listings = [
        listing
        for listing in current_listings
        if listing not in previous_listings
    ]

    if new_listings:
        print("NEW LISTINGS FOUND!")

        for listing in new_listings:
            print(listing)

        send_notification(new_listings)

    else:
        print("No new listings.")

    save_current(current_listings)


if __name__ == "__main__":
    main()
