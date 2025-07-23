import os
import time
import base64
import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

def send_email(subject, html_content, image_data_list):
    mailjet = Client(auth=(MJ_APIKEY_PUBLIC, MJ_APIKEY_PRIVATE), version='v3.1')

    attachments = []
    for i, img_data in enumerate(image_data_list):
        attachments.append({
            "ContentType": "image/png",
            "Filename": f"product_{i}.png",
            "Base64Content": img_data.decode('utf-8')
        })

    data = {
        'Messages': [
            {
                "From": {"Email": ALERT_EMAIL, "Name": "Lightbox Restock Bot"},
                "To": [{"Email": ALERT_EMAIL}],
                "Subject": subject,
                "HTMLPart": html_content,
                "Attachments": attachments
            }
        ]
    }

    result = mailjet.send.create(data=data)
    if result.status_code == 200:
        print("Alert email sent!")
    else:
        print("Failed to send email:", result.status_code, result.json())

def main():
    print("Starting Lightbox restock watcher...")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        seen_products = load_seen_products()
        print(f"Loaded {len(seen_products)} seen products.")

        driver.get(CHECK_URL)
        time.sleep(5)  # wait for page load

        product_elements = driver.find_elements(By.CSS_SELECTOR, "div.grid-product")

        new_products = []
        images_base64 = []

        for product in product_elements:
            try:
                link_el = product.find_element(By.CSS_SELECTOR, "a.grid-product__link")
                product_link = link_el.get_attribute("href")

                if product_link not in seen_products:
                    print(f"New product detected: {product_link}")
                    new_products.append(product_link)

                    driver.execute_script("arguments[0].scrollIntoView(true);", product)
                    time.sleep(1)

                    screenshot = product.screenshot_as_png
                    encoded_img = base64.b64encode(screenshot)
                    images_base64.append(encoded_img)

                    seen_products.add(product_link)

            except Exception as e:
                print("Error processing product element:", e)

        if new_products:
            html_content = "<h2>Lightbox New/Restocked Products Detected:</h2><ul>"
            for i, link in enumerate(new_products):
                html_content += f'<li><a href="{link}">{link}</a><br><img src="cid:product_{i}.png" style="max-width:400px"/></li>'
            html_content += "</ul>"

            send_email("Lightbox Restock Alert", html_content, images_base64)
            save_seen_products(seen_products)
        else:
            print("No new or restocked products.")

    finally:
        driver.quit()

if __name__ == "__main__":
    est = pytz.timezone('US/Eastern')

    while True:
        now = datetime.datetime.now(est)
        # Run between 7:00 AM - 11:59 PM and 12:00 AM - 2:59 AM (3 AM)
        if (7 <= now.hour <= 23) or (0 <= now.hour < 3):
            print(f"Current time {now.strftime('%H:%M:%S')} EST - Running check...")
            main()
            print("Sleeping 10 minutes...")
            time.sleep(600)  # 10 minutes
        else:
            # Sleep longer outside active hours (3 AM - 7 AM)
            print(f"Current time {now.strftime('%H:%M:%S')} EST - Outside active hours, sleeping 30 minutes...")
            time.sleep(1800)
