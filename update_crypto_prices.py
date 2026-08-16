"""
Update live crypto prices in the "Crypto Portfolio" Notion database.

Reads the current USD price for each coin from CoinGecko's free public API,
then writes it into the "Current Price" property of the matching Notion page.

Requires the environment variable NOTION_TOKEN (a Notion internal
integration secret that has been shared/connected to the database).
"""

import os
import sys

import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_VERSION = "2022-06-28"

# Each entry maps a Notion page (one row in the database) to its
# CoinGecko coin id, which is what the price API expects.
COINS = [
    {"page_id": "3bea057a-abc9-81a1-8c97-e384dc167a4a", "coingecko_id": "bitcoin", "name": "Bitcoin"},
    {"page_id": "3bea057a-abc9-8194-9b02-de17b9c81b43", "coingecko_id": "ethereum", "name": "Ethereum"},
    {"page_id": "3bea057a-abc9-81b9-9a2b-fae28715d647", "coingecko_id": "chainlink", "name": "Chainlink"},
    {"page_id": "3bea057a-abc9-817f-a6b0-d36c42425529", "coingecko_id": "sonic-3", "name": "Sonic"},
]


def fetch_prices() -> dict:
    ids = ",".join(coin["coingecko_id"] for coin in COINS)
    url = "https://api.coingecko.com/api/v3/simple/price"
    resp = requests.get(url, params={"ids": ids, "vs_currencies": "usd"}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def update_notion_price(page_id: str, price: float) -> None:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    payload = {"properties": {"Current Price": {"number": price}}}
    resp = requests.patch(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


def main() -> None:
    if not NOTION_TOKEN:
        print("Missing NOTION_TOKEN environment variable.", file=sys.stderr)
        sys.exit(1)

    prices = fetch_prices()

    had_error = False
    for coin in COINS:
        price = prices.get(coin["coingecko_id"], {}).get("usd")
        if price is None:
            print(f"WARNING: no price returned for {coin['name']} ({coin['coingecko_id']})")
            had_error = True
            continue
        try:
            update_notion_price(coin["page_id"], price)
            print(f"OK: {coin['name']} -> ${price}")
        except requests.HTTPError as exc:
            print(f"ERROR updating {coin['name']}: {exc} | {exc.response.text}")
            had_error = True

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
