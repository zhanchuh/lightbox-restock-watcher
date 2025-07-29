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
SEEN_PRODUCTS_FILE = "seen_products.txt"

def load_seen_products():
    if not os.path.exists(SEEN_PRODUCTS_FILE):
        return set()
    with open(SEEN_PRODUCTS_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_seen_products(products):
    with open(SEEN_PRODUCTS_FILE, "w") as f:
        for p in products:
            f.write(p + "\n")

def send_email(subject, html_content):
    mailjet = Client(auth=(MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {"Email": ALERT_EMAIL, "Name": "Lightbox Restock Bot"},
                "To": [{"Email": ALERT_EMAIL}],
                "Subject": subject,
                "HTMLPart": html_content
            }
        ]
    }
    result = mailjet.send.create(data=data)
    if result.status_code == 200:
        print("✅ Alert email sent!")
    else:
        print("❌ Failed to send email:", result.status_code, result.json())

def check_products():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking Lightbox products...")

    seen_products = load_seen_products()

    try:
        resp = requests.get(CHECK_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Error fetching URL: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    product_links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/collections/all/products/" in href:
            if not href.startswith("http"):
                href = "https://lightboxjewelry.com" + href
            product_links.add(href.split("?")[0])  # Remove variant/query params

    new_products = product_links - seen_products

    if new_products:
        print(f"🚨 Found {len(new_products)} new product(s)!")
        html_content = "<h2>🆕 Lightbox Restocked or New Products:</h2><ul>"
        for link in new_products:
            html_content += f'<li><a href="{link}">{link}</a></li>'
        html_content += "</ul>"

        send_email("🛍️ Lightbox Restock Alert", html_content)

        seen_products.update(new_products)
        save_seen_products(seen_products)
    else:
        print("No new or restocked products.")

def main():
    while True:
        utc_hour = datetime.utcnow().hour
        pst_hour = (utc_hour - 7) % 24  # PDT adjustment (UTC-7)

        if 4 <= pst_hour < 15:
            check_products()
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏰ Outside 4AM–3PM PST, skipping.")
        time.sleep(1)

if __name__ == "__main__":
    main()
