#!/usr/bin/env python3
import os
import time
import logging
import requests
from prometheus_client import start_http_server, Gauge

# Configuration
API_TOKEN = os.getenv("STARLING_API_TOKEN")
BASE_URL = "https://api.starlingbank.com/api/v2"
POLL_PERIOD = int(os.getenv("POLL_PERIOD_SECONDS", "30"))
EXPORT_PORT = int(os.getenv("EXPORTER_PORT", "8000"))

if not API_TOKEN:
    raise RuntimeError("Please set STARLING_API_TOKEN environment variable")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Prometheus Metrics
main_balance_gauge = Gauge(
    'starling_main_account_balance',
    'Starling main current account balance',
    ['currency']
)
space_balance_gauge = Gauge(
    'starling_space_balance',
    'Starling Space balance',
    ['space_name', 'currency']
)

def get_account_uid():
    url = f"{BASE_URL}/accounts"
    logging.debug(f"Fetching account UIDs from {url}")
    resp = requests.get(url, headers=HEADERS)
    logging.debug(f"Accounts response status: {resp.status_code}, payload: {resp.text}")
    resp.raise_for_status()
    accounts = resp.json().get("accounts", [])
    logging.debug(f"Accounts payload: {accounts}")
    if not accounts:
        logging.error("No accounts returned by Starling API")
        raise RuntimeError("No accounts returned by Starling API")
    return accounts[0]["accountUid"]

def fetch_main_balance(account_uid):
    url = f"{BASE_URL}/accounts/{account_uid}/balance"
    logging.debug(f"Fetching main balance from {url}")
    resp = requests.get(url, headers=HEADERS)
    logging.debug(f"Main balance status: {resp.status_code}, payload: {resp.text}")
    resp.raise_for_status()
    data = resp.json()

    curr = data.get("currency") or data.get("effectiveBalance", {}).get("currency") or data.get("clearedBalance", {}).get("currency")
    if not curr:
        logging.error("Couldn't find currency in balance payload: %s", data)
        raise KeyError("currency")
    minor = data.get("effectiveBalance", {}).get("minorUnits") or data.get("clearedBalance", {}).get("minorUnits")
    if minor is None:
        logging.error("Couldn't find minorUnits in balance payload: %s", data)
        raise KeyError("minorUnits")
    logging.debug(f"Main balance parsed: minor={minor}, curr={curr}")
    return minor / 100.0, curr

def fetch_spaces(account_uid):
    url = f"{BASE_URL}/account/{account_uid}/spaces"
    logging.debug(f"Fetching spaces from {url}")
    resp = requests.get(url, headers=HEADERS)
    logging.debug(f"Spaces response status: {resp.status_code}, payload: {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    logging.debug(f"Raw spaces data: {data}")

    # Combine savingsGoals and spendingSpaces
    raw_savings = data.get("savingsGoals", [])
    raw_spending = data.get("spendingSpaces", [])
    all_spaces = raw_savings + raw_spending
    logging.debug(f"Found {len(raw_savings)} savingsGoals and {len(raw_spending)} spendingSpaces")

    results = []
    for s in all_spaces:
        logging.debug(f"Processing space item: {s}")
        name = s.get("name") or s.get("savingsGoalUid") or s.get("spaceUid") or "unknown"
        # Determine amount field
        amount = s.get("totalSaved") or s.get("amount") or s.get("currentBalance") or {}
        minor = amount.get("minorUnits")
        curr = amount.get("currency")
        if minor is None or curr is None:
            logging.warning(f"Skipping space with incomplete data: {s}")
            continue
        logging.debug(f"Parsed space '{name}' with minor={minor}, currency={curr}")
        results.append({
            "name": name,
            "minor": minor,
            "currency": curr
        })
    return results

def main():
    # Set up debug logging
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")
    logging.info(f"Starting Starling exporter on :{EXPORT_PORT}, polling every {POLL_PERIOD}s")
    start_http_server(EXPORT_PORT)

    account_uid = get_account_uid()
    logging.info(f"Using accountUid: {account_uid}")

    seen_spaces = set()
    while True:
        try:
            bal, curr = fetch_main_balance(account_uid)
            main_balance_gauge.labels(currency=curr).set(bal)

            spaces = fetch_spaces(account_uid)
            current_names = {sp["name"] for sp in spaces}
            # Remove old spaces
            for old in seen_spaces - current_names:
                # currency label arg can be wildcard replaced by iterating existing labels if needed
                try:
                    space_balance_gauge.remove(space_name=old, currency="GBP")
                except KeyError:
                    pass
            seen_spaces.clear()

            for sp in spaces:
                space_balance_gauge.labels(
                    space_name=sp["name"], currency=sp["currency"]
                ).set(sp["minor"] / 100.0)
                seen_spaces.add(sp["name"])

        except Exception as e:
            logging.error(f"Error in main loop: {e}", exc_info=True)
        time.sleep(POLL_PERIOD)

if __name__ == "__main__":
    main()

