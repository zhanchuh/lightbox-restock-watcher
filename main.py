import os
import time
import requests
from bs4 import BeautifulSoup
from mailjet_rest import Client
from datetime import datetime

# Constants
CHECK_URLS = {
    "Jewelry": "https://lightboxjewelry.com/collections/all",
    "Loose Diamonds": "https://lightboxjewelry.com/collections/lab-grown-loose-diamonds"
}
ALERT_EMAIL = os.getenv("ALERT_EMAIL")
MJ_APIKEY_PUBLIC = os.getenv("MJ_APIKEY_PUBLIC")
MJ_APIKEY_PRIVATE = os.getenv("MJ_APIKEY_PRIVATE")
SEEN_PRODUCTS_FILE = "seen_products.txt"

# Load previously seen product links
def load_seen_products():
    if not os.path.exists(SEEN_PRODUCTS_FILE):
        return set()
    with open(SEEN_PRODUCTS_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

# Save updated list of product links
def save_seen_products(products):
    with open(SEEN_PRODUCTS_FILE, "w") as f:
        for p in products:
            f.write(p + "\n")

# Send an email alert
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

# Core check function
def check_products():
    print(f"\nCurrent time {datetime.now().strftime('%H:%M:%S')} - Running check...")

    seen_products = load_seen_products()
    current_links = set()
    categorized_links = {"Jewelry": set(), "Loose Diamonds": set()}

    for category, url in CHECK_URLS.items():
        try:
            resp = requests.get(url)
            resp.raise_for_status()
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/products/" in href:
                if not href.startswith("http"):
                    href = "https://lightboxjewelry.com" + href
                clean_link = href.split("?")[0]
                current_links.add(clean_link)
                categorized_links[category].add(clean_link)

    new_products = current_links - seen_products
    if new_products:
        print(f"🚨 Found {len(new_products)} new product(s)!")
        html_content = "<h2>🆕 Lightbox Restocked or New Products:</h2>"

        for category in categorized_links:
            new_in_category = categorized_links[category] & new_products
            if new_in_category:
                html_content += f"<h3>{category}:</h3><ul>"
                for link in sorted(new_in_category):
                    html_content += f'<li><a href="{link}">{link}</a></li>'
                html_content += "</ul>"

        send_email("🛍️ Lightbox Restock Alert", html_content)
        save_seen_products(current_links)
    else:
        print("No new or restocked products.")

# Main loop (4 AM to 3 PM PST)
def main():
    while True:
        current_hour_utc = datetime.utcnow().hour
        current_hour_pst = (current_hour_utc - 7) % 24  # PST = UTC-7

        if 4 <= current_hour_pst < 15:
            check_products()
        else:
            print("⏰ Outside of check hours (4AM–3PM PST), skipping this run.")

        time.sleep(1)  # Check every second

if __name__ == "__main__":
    main()
