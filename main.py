import os
import time
import requests
from bs4 import BeautifulSoup
from mailjet_rest import Client

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
        print("Alert email sent!")
    else:
        print("Failed to send email:", result.status_code, result.json())

def main():
    print("Checking Lightbox products...")

    seen_products = load_seen_products()
    print(f"Loaded {len(seen_products)} seen products.")

    resp = requests.get(CHECK_URL)
    if resp.status_code != 200:
        print(f"Failed to fetch page: {resp.status_code}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    product_links = set()

    # Adjust selector if needed, this matches product links on Lightbox site
    for a in soup.select("a.grid-product__link"):
        href = a.get("href")
        if href and href.startswith("/products/"):
            full_link = "https://lightboxjewelry.com" + href
            product_links.add(full_link)

    new_products = product_links - seen_products

    if new_products:
        print(f"Found {len(new_products)} new products!")
        html_content = "<h2>Lightbox New/Restocked Products Detected:</h2><ul>"
        for link in new_products:
            html_content += f'<li><a href="{link}">{link}</a></li>'
        html_content += "</ul>"

        send_email("Lightbox Restock Alert", html_content)

        seen_products.update(new_products)
        save_seen_products(seen_products)
    else:
        print("No new or restocked products.")

if __name__ == "__main__":
    main()
