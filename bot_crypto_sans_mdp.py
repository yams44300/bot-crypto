import os
import requests
import time
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText

print("Bot lancé ✔️")

URL = "https://api.bitvavo.com/v2/ticker/24h"

positions = {}
previous_prices = {}

# =========================
# EMAIL CONFIG
# =========================
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

def send_email(subject, message):
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)

        print("📩 EMAIL SENT")

    except Exception as e:
        print("❌ EMAIL ERROR:", e)

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

if not sheet.get("A1"):
    sheet.update("A1:F1", [[
        "Date","Crypto","Prix","Variation %","Volume","Status"
    ]])

# =========================
# FUNCTIONS
# =========================
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
            round(change, 2),
            volume,
            status
        ])
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

                price_raw = coin.get("last")
                volume_raw = coin.get("volume")

                if price_raw is None or volume_raw is None:
                    continue

                price = float(price_raw)
                volume = float(volume_raw)

                if price == 0 or volume == 0:
                    continue

                old_price = previous_prices.get(market, price)
                change_short = ((price - old_price) / old_price) * 100
                previous_prices[market] = price

                change_24h = float(coin.get("priceChangePercentage") or 0)

                # =========================
                # FILTRE LIQUIDITÉ
                # =========================
                if volume < 20000:
                    continue

                # =========================
                # FILTRE VOLATILITÉ
                # =========================
                if abs(change_short) > 6:
                    continue

                # =========================
                # 🎯 BUY
                # =========================
                if change_short <= -2 and market not in positions:

                    positions[market] = price

                    print(f"🔥 BUY {market} {change_short:.2f}%")

                    log_event(market, price, change_short, volume, "BUY")

                    # 📩 MAIL BUY
                    send_email(
                        "🚨 BUY DETECTÉ",
                        f"{market}\nPrix: {price}\nVariation: {round(change_short,2)}%"
                    )

                # =========================
                # 💰 SELL
                # =========================
                if market in positions:
                    entry = positions[market]
                    gain = ((price - entry) / entry) * 100

                    if gain >= 2.5:

                        print(f"💰 SELL {market} +{gain:.2f}%")

                        log_event(market, price, gain, volume, "SELL +2.5%")

                        # 📩 MAIL SELL
                        send_email(
                            "💰 SELL DETECTÉ",
                            f"{market}\nGain: {round(gain,2)}%"
                        )

                        del positions[market]

            except Exception as e:
                print("Erreur coin:", e)

    except Exception as e:
        print("Erreur globale:", e)

    time.sleep(60)
