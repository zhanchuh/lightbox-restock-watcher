import requests
from bs4 import BeautifulSoup
import smtplib
import json
import time
import os
import ssl
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

COLLECTION_URL = "https://www.lightboxjewelry.com/collections/all"
CHECK_INTERVAL = 1800  # 30 minutes

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

SNAPSHOT_FILE = "product_snapshot.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_products():
    response = requests.get(COLLECTION_URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")

    products = {}
    product_cards = soup.find_all("a", class_="ProductItem__ImageWrapper")  # Confirm class if needed

    for card in product_cards:
        product_url = "https://www.lightboxjewelry.com" + card['href']
        title = card.get("aria-label") or card.img.get("alt", "Unknown Product")

        product_page = requests.get(product_url, headers=HEADERS)
        product_soup = BeautifulSoup(product_page.content, "html.parser")
        in_stock = "Add to Bag" in product_soup.text  # Adjust if necessary

        products[title] = {
            "url": product_url,
            "in_stock": in_stock
        }

    return products

def load_snapshot():
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r") as f:
            return json.load(f)
    return {}

def save_snapshot(data):
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def capture_screenshot(url, title):
    os.makedirs("screenshots", exist_ok=True)
    filename = f"{title[:50].replace(' ', '_').replace('/', '')}.png"
    path = os.path.join("screenshots", filename)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.get(url)
    time.sleep(3)
    driver.save_screenshot(path)
    driver.quit()

    return path

def send_email_with_attachments(subject, body, image_paths):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(body)

    for image_path in image_paths:
        with open(image_path, "rb") as f:
            img_data = f.read()
            msg.add_attachment(
                img_data,
                maintype="image",
                subtype="png",
                filename=os.path.basename(image_path)
            )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)

def compare_snapshots(old, new):
    restocks = []
    new_products = []

    for name, info in new.items():
        if name not in old:
            new_products.append((name, info))
        elif not old[name]["in_stock"] and info["in_stock"]:
            restocks.append((name, info))

    return restocks, new_products

def main():
    while True:
        try:
            print("Checking Lightbox products...")
            new_snapshot = fetch_products()
            old_snapshot = load_snapshot()

            restocks, new_products = compare_snapshots(old_snapshot, new_snapshot)

            all_changes = restocks + new_products

            if all_changes:
                image_paths = []
                email_lines = []

                for label, (name, info) in zip(
                    ["RESTOCKED"] * len(restocks) + ["NEW"] * len(new_products),
                    all_changes
                ):
                    line = f"{label}: {name}\n{info['url']}"
                    email_lines.append(line)
                    image_paths.append(capture_screenshot(info["url"], name))

                body = "\n\n".join(email_lines)
                send_email_with_attachments("🔔 Lightbox Alert: New or Restocked Products", body, image_paths)
                print("Email sent with screenshots.")

            else:
                print("No new or restocked products.")

            save_snapshot(new_snapshot)

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
