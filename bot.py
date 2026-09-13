import os
import time
import re
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
    "https://www.chroniclelive.co.uk/news/?service=rss",
    "https://www.glasgowtimes.co.uk/news/rss/",
    "https://www.edinburghnews.scotsman.com/rss",
    "https://www.nottinghampost.com/news/?service=rss",
    "https://www.sunderlandecho.com/news/rss",
    "https://www.birminghammail.co.uk/news/?service=rss",
    "https://www.leicestermercury.co.uk/news/?service=rss"
]

# Expanded Keyword List including your additions
KEYWORDS = [
    # Original legal/court & crime terms
    "court", "trial", "judge", "sentence", "prison", "hearing", 
    "inquest", "crime", "jury", "offense", "offence",
    "robbery", "fight", "attack", "knife", "rape", "assault", "race", 
    "hurt", "punch", "gun", "stabbing", "murder", "machete", "brawl", 
    "gang", "shooting", "arrest", "charged", "investigation", "weapon", 
    "thief", "burglary", "cops", "detectives", "tragedy", "tragic", "hotspot",
    # User-added terms
    "rightwing", "leftwing", "just in", "breaking news", 
    "sex attack", "counter fit", "counterfeit", "police"
]

# Map feed sources or locations to readable labels
LOCATION_KEYWORDS = {
    "manchestereveningnews": "Manchester",
    "leeds-live": "Leeds",
    "liverpoolecho": "Liverpool",
    "chroniclelive": "Newcastle",
    "glasgowtimes": "Glasgow",
    "edinburghnews": "Edinburgh",
    "nottinghampost": "Nottingham",
    "sunderlandecho": "Sunderland",
    "birminghammail": "Birmingham",
    "leicestermercury": "Leicester",
    "judiciary.uk": "UK Courts",
    "bbci.co.uk": "National UK"
}

seen_articles = set()

def detect_location(feed_url, text):
    for domain, loc in LOCATION_KEYWORDS.items():
        if domain in feed_url:
            return loc
            
    text_lower = text.lower()
    cities = [
        "manchester", "london", "glasgow", "edinburgh", "nottingham", 
        "newcastle", "sunderland", "birmingham", "leicester", "leeds", 
        "liverpool", "cardiff", "belfast", "sheffield", "bristol"
    ]
    for city in cities:
        if city in text_lower:
            return city.capitalize()
            
    return "UK"

def clean_html(raw_html):
    if not raw_html:
        return ""
    # Convert breaks and paragraphs to newlines
    clean = re.sub(r'<br\s*/?>', '\n', raw_html)
    clean = re.sub(r'</p>', '\n\n', clean)
    # Strip remaining HTML tags so Telegram doesn't crash on bad formatting
    clean = re.sub(r'<.*?>', '', clean)
    return clean.strip()

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
                        
                        # Extract the longest available content block or summary
                        raw_content = ""
                        if hasattr(entry, 'content') and entry.content:
                            raw_content = entry.content[0].get('value', '')
                        elif hasattr(entry, 'summary'):
                            raw_content = entry.summary
                        elif hasattr(entry, 'description'):
                            raw_content = entry.description
                            
                        body_text = clean_html(raw_content)
                        combined_text = (title + " " + body_text).lower()
                        
                        if any(kw in combined_text for kw in KEYWORDS):
                            location = detect_location(feed_url, combined_text)
                            
                            # Maximize length safely under Telegram's 4096 char limit
                            max_body_length = 3200
                            if len(body_text) > max_body_length:
                                body_text = body_text[:max_body_length] + "..."
                            
                            message = (
                                f"🚨 <b>{location} Alert</b>\n\n"
                                f"<b>{title}</b>\n\n"
                                f"{body_text}\n\n"
                                f"<a href='{link}'>Read full story on site</a>"
                            )
                            
                            send_telegram_message(message)
                            print(f"Alert posted [{location}]: {title}")
                            time.sleep(1)
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        time.sleep(300)

if __name__ == "__main__":
    run_bot()
