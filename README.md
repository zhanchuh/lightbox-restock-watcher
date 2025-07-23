# Lightbox Restock Watcher Bot

Monitors Lightbox Jewelry for new or restocked products, takes screenshots, and sends email alerts.

## Setup

1. Create a GitHub repo and add these files (`main.py`, `requirements.txt`, `README.md`).

2. Deploy to Railway.app or your favorite Python environment.

3. Add these environment variables securely:
   - `EMAIL_FROM` (your Gmail address)
   - `EMAIL_TO` (your email to receive alerts)
   - `EMAIL_PASSWORD` (Gmail App Password)

4. Run the bot!

## Notes

- Requires ChromeDriver managed automatically by `webdriver-manager`.
- Uses Gmail SMTP for sending emails.
- Screenshots saved in the `screenshots/` folder.
- Checks every 30 minutes by default.

