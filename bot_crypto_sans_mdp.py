import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import csv
import json
import gspread
from google.oauth2.service_account import Credentials

print("Bot lancé ✔️")
print("GOOGLE_CREDS =", os.getenv("GOOGLE_CREDS"))

URL = "https://api.bitvavo.com/v2/ticker/24h"

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

# 👉 mémoire courte (scalping)
previous_prices = {}
last_alert_time = {}
positions = {}

# 🔥 CONFIG GOOGLE SHEETS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.getenv("GOOGLE_CREDS"))

creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

client = gspread.authorize(creds)

sheet = client.open_by_key("1Xvzy0NQdSu9UuztJaEqRZFSokPFHZvRFHjDy8_5YtkI").sheet1
sheet.append_row(["TEST", "OK"])

# 👉 évite spam (1 alerte / 10 min max par coin)
ALERT_COOLDOWN = 600

def send_email(message):
    try:
        msg = MIMEText(message)
        msg["Subject"] = "🚨 DUMP CRYPTO DETECTÉ"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        print("Email error:", e)

def get_data():
    try:
        return requests.get(URL, timeout=10).json()
    except Exception as e:
        print("API error:", e)
        return []

def scan_dumps():
    data = get_data()
    signals = []

    for coin in data:
        try:
            market = coin["market"]
            price = float(coin["last"])
            volume = float(coin.get("volume", 0))

            # init
            if market not in previous_prices:
                previous_prices[market] = price
                continue

            old_price = previous_prices[market]

            # variation courte
            change = ((price - old_price) / old_price) * 100

            print(market, change)

            # update prix
            previous_prices[market] = price

            # ⛔ filtre volume (anti fake dump)
            if volume < 80000:
                continue

            # 🚨 DUMP SIGNIFICATIF
            if change <= -5:
                now = time.time()

                # anti spam
                if market in last_alert_time:
                    if now - last_alert_time[market] < ALERT_COOLDOWN:
                        continue

                last_alert_time[market] = now

                positions[market] = price
                
                log_event(market, price, change, volume, "DUMP")
                
                signals.append({
                    "market": market,
                    "price": price,
                    "change": change,
                    "volume": volume
                })

        except Exception as e:
            continue

    return signals


def log_event(market, price, change, volume, status):
    try:
        sheet.append_row([
            str(datetime.now()),
            market,
            price,
            change,
            volume,
            status
        ])
    except Exception as e:
        print("Google Sheets error:", e)

        writer.writerow([
            datetime.now(),
            market,
            price,
            change,
            volume,
            status
        ])

while True:
    print("Scan en cours...", datetime.now())

    try:
        dumps = scan_dumps()

        print("Positions :", positions)
        
        for market, entry_price in list(positions.items()):
            current_price = previous_prices.get(market)

            if not current_price:
                continue

            change = ((current_price - entry_price) / entry_price) * 100

            if change >= 5:
                print(f"💰 EXIT {market} +5%")

                log_event(market, current_price, change, 0, "EXIT +5%")

                del positions[market]

        if dumps:
            message = "🚨 DUMP DETECTÉ (SCALPING ENTRY)\n\n"

            for d in dumps:
                message += f"{d['market']} | {d['change']:.2f}% | price: {d['price']}\n"

            print(message)

            send_email(message)

        else:
            print("Aucun dump")

    except Exception as e:
        print("Erreur globale :", e)

    # 👉 IMPORTANT : léger pour Railway free tier
    time.sleep(60)
