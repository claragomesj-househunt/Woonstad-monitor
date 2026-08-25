import hashlib
import json
import os
import re
import urllib.request
from html.parser import HTMLParser

URL = "https://www.woonstadrotterdam.nl/aanbod/vrije-sector-huurwoning"
STATE_FILE = "state.json"

NTFY_TOPIC = os.environ["NTFY_TOPIC"]
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            href = attrs.get("href", "")
            if href:
                self.links.append(href)


def download_page():
    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Woonstad listing monitor)"
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def extract_listing_links(html):
    parser = LinkParser()
    parser.feed(html)

    links = set()

    for link in parser.links:
        if "woonstadrotterdam.nl" in link:
            if any(x in link.lower() for x in [
                "woning",
                "huur",
                "aanbod"
            ]):
                links.add(link)

    return sorted(links)


def load_state():
    if not os.path.exists(STATE_FILE):
        return []

    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_state(items):
    with open(STATE_FILE, "w") as f:
        json.dump(items, f, indent=2)


def notify(new_items):
    if not new_items:
        return

    message = (
        "🏠 NIEUWE WOONSTAD WONING!\n\n"
        + "\n".join(new_items[:10])
        + "\n\n"
        + URL
    )

    request = urllib.request.Request(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": "Nieuwe Woonstad woning",
            "Priority": "urgent",
            "Tags": "house",
            "Click": URL,
        },
        method="POST",
    )

    urllib.request.urlopen(request, timeout=30)


def main():
    html = download_page()

    listings = extract_listing_links(html)

    # Remove duplicates and sort them.
    listings = sorted(set(listings))

    old_listings = load_state()

    # First run establishes the baseline.
    if not old_listings:
        save_state(listings)
        print(f"Initial scan: {len(listings)} links saved.")
        return

    new_items = [
        item for item in listings
        if item not in old_listings
    ]

    if new_items:
        print("NEW LISTINGS:")
        for item in new_items:
            print(item)

        notify(new_items)

    save_state(listings)

    print(
        f"Checked Woonstad: {len(listings)} links, "
        f"{len(new_items)} new."
    )


if __name__ == "__main__":
    main()
