
import os
import requests
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import csv

print("CSV enregistré dans :", os.getcwd())
print("Bot lancé ✔️")

URL = "https://api.bitvavo.com/v2/ticker/24h"

# CONFIG EMAIL
EMAIL_SENDER = "yams.sono@gmail.com"
EMAIL_PASSWORD = "hegs lmkk psmk htog"
EMAIL_RECEIVER = "yams.sono@gmail.com"

def send_email(message):
    msg = MIMEText(message)
    msg["Subject"] = "🚨 Crypto DIP détecté"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

def get_data():
    return requests.get(URL).json()

previous_prices = {}

def scan_dips():
    data = get_data()
    signals = []

    for coin in data:
        try:
            market = coin["market"]
            price = float(coin["last"])

            if market in previous_prices:
                change = ((price - previous_prices[market]) / previous_prices[market]) * 100

                print(market, change)

                if change < -0.8 and volume > 50000:
                    print("⚠️ petit dip", market, change)
                if change < -1.5 and volume > 100000:
                    print("🚨 GROS DIP", market, change)
                    signals.append({
                        "market": market,
                        "price": price,
                        "change": change,
                        "volume": float(coin["volume"])
                    })

            previous_prices[market] = price

        except Exception as e:
            print("skip:", e)
            continue

    return signals

def save_to_csv(signals):
    with open("crypto_dips.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Crypto", "Prix", "24h %", "Volume", "Date", "Status"])

        for s in signals:
            writer.writerow([
                s["market"],
                s["price"],
                s["change"],
                s["volume"],
                datetime.now(),
                "DIP"
            ])
while True:
    print("Scan en cours...", datetime.now())

    try:
        dips = scan_dips()

        if dips:
            message = "📉 DIPS DÉTECTÉS :\n\n"

            for d in dips:
                message += f"{d['market']} | {d['change']}% | prix: {d['price']}\n"

            print(message)

            send_email(message)
            save_to_csv(dips)

        else:
            print("Aucun signal")

            with open("crypto_dips.csv", "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "-",
                    "-",
                    "-",
                    "-",
                    datetime.now(),
                    "Aucun signal"
                ])

    except Exception as e:
        print("Erreur :", e)

    time.sleep(60)