import os
import time
import feedparser
import requests

# Configuration from Railway Environment Variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Comprehensive List of RSS Feeds (National news, Courts, and Regional UK feeds)
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "https://www.judiciary.uk/rss-feeds/",
    "https://www.manchestereveningnews.co.uk/news/?service=rss",
    "https://www.leeds-live.co.uk/news/?service=rss",
    "https://www.liverpoolecho.co.uk/news/?service=rss",
    "https://www.myportsmouth.co.uk/news/rss", # Regional coverage placeholder/standard format
    "https://www.chroniclelive.co.uk/news/?service=rss", # Newcastle
    "https://www.glasgowtimes.co.uk/news/rss/", # Glasgow
    "https://www.edinburghnews.scotsman.com/rss", # Edinburgh
    "https://www.nottinghampost.com/news/?service=rss", # Nottingham
    "https://www.sunderlandecho.com/news/rss", # Sunderland
    "https://www.birminghammail.co.uk/news/?service=rss", # Birmingham
    "https://www.leicestermercury.co.uk/news/?service=rss" # Leicester
]

# Comprehensive Keywords for crime, courts, and major incidents
KEYWORDS = [
    "court", "trial", "judge", "police", "sentence", "prison", "hearing", 
    "inquest", "crime", "jury", "robbery", "fight", "attack", "knife", 
    "rape", "assault", "race", "hurt", "punch", "gun", "shooting", 
    "stabbing", "murder", "machete", "brawl", "gang", "offense"
]

seen_articles = set()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def run_bot():
    print("Bot started. Running loop...")
    while True:
        print("Scanning feeds for new updates...")
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    article_id = entry.id if 'id' in entry else entry.link
                    title = entry.title
                    link = entry.link

                    if article_id not in seen_articles:
                        seen_articles.add(article_id)
                        
                        summary = entry.summary if 'summary' in entry else ""
                        combined_text = (title + " " + summary).lower()
                        
                        if any(kw in combined_text for kw in KEYWORDS):
                            message = f"🚨 <b>New Alert</b>\n\n<b>{title}</b>\n\n{link}"
                            send_telegram_message(message)
                            print(f"New alert posted: {title}")
                            time.sleep(1) # Prevent flooding Telegram API
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        # Wait 5 minutes before checking again
        time.sleep(300)

if __name__ == "__main__":
    run_bot()
