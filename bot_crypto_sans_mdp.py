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

# GOOGLE SHEETS
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
client = gspread.authorize(creds)

sheet = client.open_by_key("1Xvzy0NQdSu9UuztJaEqRZFSokPFHZvRFHjDy8_5YtkI").worksheet("TRADES")

# Header une seule fois
# Header (une seule fois)
if not sheet.get("A1"):
    sheet.update("A1:F1", [[
        "Date","Crypto","Prix","Variation %","Volume","Status"
    ]])

def get_data():
    try:
        return requests.get(URL, timeout=10).json()
    except:
        return []

def log_event(market, price, change, volume, status):
    try:
        sheet.append_row([
            str(datetime.now()),
            market,
            price,
            change,
            round(change, 2),
            volume,
            status
        ])
        print(f"📊 LOGGED: {market} {status}")
    except Exception as e:
        print("Sheets error:", e)

while True:
    print("Scan...", datetime.now())

    try:
        data = get_data()

        for coin in data:
            try:
                market = coin["market"]
                price = float(coin["last"])
                volume = float(coin.get("volume", 0))
                change = float(coin.get("priceChangePercentage", 0))

                # variations
                old_price = previous_prices.get(market, price)

                # variation courte (TRÈS IMPORTANT)
                change_short = ((price - old_price) / old_price) * 100

                # variation 24h
                change_24h = float(coin.get("priceChangePercentage", 0))

                previous_prices[market] = price

                # filtre volume (plus souple)
                # filtre liquidité
                if volume < 20000:
                   continue
                   
                # 🎯 VRAI DUMP (court terme)
                if change_short <= -4 and market not in positions:

                   positions[market] = price

                   print(f"🔥 BUY {market} SHORT {change_short:.2f}%")

                   log_event(market, price, change_short, volume, "BUY")

                # 🎯 EXIT +5%
                continue

                # =========================
                # 🟢 STRAT 1 : REBOUND
                # =========================
                if (
                    change_short <= -5 and
                    change_24h < -2 and
                    market not in positions
                ):
                    positions[market] = price

                    print(f"🟢 REBOUND BUY {market} {change_short:.2f}%")

                    log_event(market, price, change_short, volume, "BUY REBOUND")

                # =========================
                # 🔵 STRAT 2 : PULLBACK
                # =========================
                if (
                    change_short <= -4 and
                    change_24h > 5 and
                    market not in positions
                ):
                    positions[market] = price

                    print(f"🔵 PULLBACK BUY {market} {change_short:.2f}%")

                    log_event(market, price, change_short, volume, "BUY PULLBACK")

                # =========================
                # 💰 EXIT
                # =========================
                if market in positions:
                    entry = positions[market]
                    gain = ((price - entry) / entry) * 100

                    if gain >= 5:
                        print(f"💰 SELL {market} +{gain:.2f}%")

                        log_event(market, price, gain, volume, "SELL +5%")
                       

                        del positions[market]

            except:
            except Exception as e:
                continue

    except Exception as e:
        print("Erreur:", e)

    time.sleep(60)
