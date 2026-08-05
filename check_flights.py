import requests
from bs4 import BeautifulSoup
import json
import os
import sys

URL = "https://www.tustus.co.il/Arkia/Home"
STATE_FILE = "data/previous_flights.json"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_flights():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = {}
    for el in soup.find_all(attrs={"ite_item": True}):
        item_id = el.get("ite_item", "").strip()
        if not item_id:
            continue
        name = el.get("data_ga_item_name", "").strip()
        brand = el.get("data_ga_item_brand", "").strip()  # date range
        price = el.get("data_number_ga_price", "").strip()
        items[item_id] = {
            "id": item_id,
            "name": name,
            "dates": brand,
            "price": price,
        }
    return items


def load_previous():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_current(items):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID env vars, skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": True,
    }, timeout=15)
    if resp.status_code != 200:
        print(f"Failed to send Telegram message: {resp.status_code} {resp.text}", file=sys.stderr)


def main():
    current = fetch_flights()
    previous = load_previous()

    new_ids = set(current.keys()) - set(previous.keys())

    if new_ids:
        lines = ["\u2708\ufe0f \u05e0\u05de\u05e6\u05d0\u05d5 \u05d8\u05d9\u05e1\u05d5\u05ea \u05d7\u05d3\u05e9\u05d5\u05ea \u05d1-tustus.co.il:\n"]
        for iid in new_ids:
            item = current[iid]
            lines.append(
                f"\U0001F6EB {item['name']}\n"
                f"\U0001F4C5 {item['dates']}\n"
                f"\U0001F4B0 ${item['price']}\n"
            )
        lines.append(URL)
        message = "\n".join(lines)
        print(message)
        send_telegram(message)
    else:
        print(f"No new flights found. Currently tracking {len(current)} unique items.")

    save_current(current)


if __name__ == "__main__":
    main()
