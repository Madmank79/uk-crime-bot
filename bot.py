import os
import time
import feedparser
import requests

# Configuration from Railway Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# List of RSS feeds (including UK news and court/legal updates)
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "https://www.judiciary.uk/rss-feeds/",
]

SEEN_FILE = "seen_articles.txt"


def load_seen_articles():
  if not os.path.exists(SEEN_FILE):
    return set()
  with open(SEEN_FILE, "r") as f:
    return set(line.strip() for line in f)


def save_seen_article(article_id):
  with open(SEEN_FILE, "a") as f:
    f.write(article_id + "\n")


def send_telegram_message(text):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Telegram connection error: {e}")


def check_feeds():
  seen = load_seen_articles()
  print("Scanning feeds for new updates...")

  for feed_url in RSS_FEEDS:
    parsed_feed = feedparser.parse(feed_url)
    for entry in parsed_feed.entries[:5]:  # Check top 5 recent entries per feed
      article_id = entry.get("id", entry.get("link"))
      title = entry.get("title", "No Title")
      link = entry.get("link", "")

      # Filter specifically for court, case, or legal elements if desired
      if article_id not in seen:
        message = f"🚨 <b>New UK Legal / News Update</b>\n\n<b>{title}</b>\n🔗 {link}"
        send_telegram_message(message)
        save_seen_article(article_id)
        print(f"New alert posted: {title}")
        time.sleep(2)


if __name__ == "__main__":
  print("Bot started. Running loop...")
  while True:
    try:
      check_feeds()
    except Exception as e:
      print(f"Error during scan loop: {e}")
    # Wait 5 minutes before scanning again (silently logs to console)
    time.sleep(300)
