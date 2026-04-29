import os
import requests
import time
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

print("Bot lancé ✔️")

URL = "https://api.bitvavo.com/v2/ticker/24h"

positions = {}
previous_prices = {}

# =========================
# GOOGLE SHEETS
# =========================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_key("1Xvzy0NQdSu9UuztJaEqRZFSokPFHZvRFHjDy8_5YtkI").worksheet("TRADES")

# Header safe init
if sheet.row_values(1) == []:
    sheet.update("A1:F1", [[
        "Date", "Crypto", "Prix", "Variation %", "Volume", "Status"
    ]])

# =========================
# DATA FETCH
# =========================

def get_data():
    try:
        r = requests.get(URL, timeout=10)
        if r.status_code != 200:
            print("API error:", r.status_code)
            return []
        return r.json()
    except Exception as e:
        print("Fetch error:", e)
        return []

# =========================
# LOG SHEETS
# =========================

def log_event(market, price, change, volume, status):
    try:
        sheet.insert_row([
            str(datetime.now()),
            market,
            price,
            round(change, 2),
            volume,
            status
        ], 2)  # 🔥 insert en haut
        print(f"📊 LOGGED: {market} {status}")
    except Exception as e:
        print("Sheets error:", e)

# =========================
# MAIN LOOP
# =========================

while True:
    print("Scan...", datetime.now())

    try:
        data = get_data()

        for coin in data:

            try:
                market = coin.get("market")
                if not market:
                    continue

                price = float(coin.get("last") or 0)
                volume = float(coin.get("volume") or 0)

                if price <= 0:
                    continue

                # =========================
                # PRICE CHANGE SAFE
                # =========================

                old_price = previous_prices.get(market)

                if old_price is None or old_price == 0:
                    previous_prices[market] = price
                    continue

                change_short = ((price - old_price) / old_price) * 100
                change_24h = float(coin.get("priceChangePercentage") or 0)

                previous_prices[market] = price

                # =========================
                # LIQUIDITY FILTER
                # =========================

                if volume < 20000:
                    continue

                # =========================
                # AVOID RE-SPAM ENTRY
                # =========================

                in_position = market in positions

                # =========================
                # 🟢 REBOUND STRATEGY
                # =========================

                if (
                    change_short <= -5 and
                    change_24h < -2 and
                    not in_position
                ):
                    positions[market] = price
                    print(f"🟢 REBOUND BUY {market} {change_short:.2f}%")
                    log_event(market, price, change_short, volume, "BUY REBOUND")

                # =========================
                # 🔵 PULLBACK STRATEGY
                # =========================

                elif (
                    change_short <= -4 and
                    change_24h > 5 and
                    not in_position
                ):
                    positions[market] = price
                    print(f"🔵 PULLBACK BUY {market} {change_short:.2f}%")
                    log_event(market, price, change_short, volume, "BUY PULLBACK")

                # =========================
                # 💰 EXIT STRATEGY
                # =========================

                if in_position:

                    entry = positions.get(market)

                    if entry and entry > 0:
                        gain = ((price - entry) / entry) * 100

                        if gain >= 5:
                            print(f"💰 SELL {market} +{gain:.2f}%")

                            log_event(market, price, gain, volume, "SELL +5%")

                            del positions[market]

            except Exception as e:
                print("Coin error:", e)
                continue

    except Exception as e:
        print("Main loop error:", e)

    time.sleep(60)
