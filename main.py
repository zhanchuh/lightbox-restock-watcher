import os
import time
import requests
from bs4 import BeautifulSoup
from mailjet_rest import Client
from datetime import datetime

CHECK_URL = os.getenv("CHECK_URL", "https://lightboxjewelry.com/collections/all")
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
MJ_APIKEY_PUBLIC = os.getenv("MJ_APIKEY_PUBLIC")
MJ_APIKEY_PRIVATE = os.getenv("MJ_APIKEY_PRIVATE")

last_seen_links = set()

def send_email(subject, new_links):
    mailjet = Client(auth=(MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE), version='v3.1')
    html_content = "<h2>🆕 New Lightbox Products:</h2><ul>"
    for link in sorted(new_links):
        html_content += f'<li><a href="{link}">{link}</a></li>'
    html_content += "</ul>"

    data = {
        'Messages': [{
            "From": {"Email": ALERT_EMAIL, "Name": "Lightbox Restock Bot"},
            "To":   [{"Email": ALERT_EMAIL}],
            "Subject": subject,
            "HTMLPart": html_content
        }]
    }

    res = mailjet.send.create(data=data)
    if res.status_code == 200:
        print("✅ Alert email sent!")
    else:
        print("❌ Email failed:", res.status_code, res.json())

def check_products():
    global last_seen_links
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] Checking Lightbox…")

    try:
        r = requests.get(CHECK_URL)
        r.raise_for_status()
    except Exception as e:
        print("❌ Fetch error:", e)
        return

    soup = BeautifulSoup(r.text, "html.parser")
    current_links = {
        ("https://lightboxjewelry.com" + a["href"].split("?")[0])
        if a["href"].startswith("/collections/all/products/")
        else a["href"].split("?")[0]
        for a in soup.find_all("a", href=True)
        if "/collections/all/products/" in a["href"]
    }

    new_links = current_links - last_seen_links
    if new_links:
        print(f"🚨 Detected {len(new_links)} new link(s).")
        send_email("🛍️ Lightbox Restock Alert", new_links)
        last_seen_links = current_links
    else:
        print("✅ No changes.")

def main():
    while True:
        hour = datetime.now().hour
        # Active window: 4 AM <= hour < 15 (3 PM)
        if 4 <= hour < 15:
            check_products()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Outside 4 AM–3 PM PST, skipping.")
        time.sleep(1)  # run every second

if __name__ == "__main__":
    main()
