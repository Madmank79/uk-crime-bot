import os
import time
import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
import re
from urllib.parse import urlparse

# --- CONFIGURATION ---
CONFIG = {
    "DB_NAME": "uk_crime_bot.db",
    "SCAN_INTERVAL_SECONDS": 600,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "MIN_P_LENGTH": 60,
    "ORACLE_ENABLED": True,
    "MAX_RETRIES": 2
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")           # Main Channel ID
TELEGRAM_ARCHIVE_CHAT_ID = os.getenv("TELEGRAM_ARCHIVE_CHAT_ID") # Second Channel ID for Full Text

# --- RSS FEEDS ---
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

KEYWORDS = [
    "court", "trial", "judge", "sentence", "prison", "hearing", 
    "inquest", "crime", "jury", "offense", "offence",
    "robbery", "fight", "attack", "knife", "rape", "assault", "race", 
    "hurt", "punch", "gun", "stabbing", "murder", "machete", "brawl", 
    "gang", "shooting", "arrest", "charged", "investigation", "weapon", 
    "thief", "burglary", "cops", "detectives", "tragedy", "tragic", "hotspot",
    "rightwing", "leftwing", "just in", "breaking news", 
    "sex attack", "counter fit", "counterfeit", "police", "assaulted", "murdered"
]

LOCATION_KEYWORDS = {
    "manchestereveningnews": "Manchester", "leeds-live": "Leeds",
    "liverpoolecho": "Liverpool", "chroniclelive": "Newcastle",
    "glasgowtimes": "Glasgow", "edinburghnews": "Edinburgh",
    "nottinghampost": "Nottingham", "sunderlandecho": "Sunderland",
    "birminghammail": "Birmingham", "leicestermercury": "Leicester",
    "judiciary.uk": "UK Courts", "bbci.co.uk": "National UK"
}

ORACLE_PREDICTIONS = [
    "The next hour will bring movement in the shadows… watch the quiet ones.",
    "Something unexpected is already on its way. Stay sharp.",
    "A small decision made this hour will echo louder than you think.",
    "Keep your eyes open — the next 60 minutes belong to the unexpected.",
    "Old patterns are about to break. The next hour is a reset.",
    "Someone is about to reveal more than they intended.",
    "The atmosphere is shifting. Act before the window closes."
]

def init_db():
    conn = sqlite3.connect(CONFIG["DB_NAME"])
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_articles (
            article_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def is_seen(article_id):
    conn = sqlite3.connect(CONFIG["DB_NAME"])
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_articles WHERE article_id = ?", (article_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_seen(article_id):
    conn = sqlite3.connect(CONFIG["DB_NAME"])
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO seen_articles (article_id) VALUES (?)", (article_id,))
    conn.commit()
    conn.close()

def get_dynamic_emoji(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["murder", "killed", "homicide", "fatal"]):
        return "💀"
    elif any(w in text_lower for w in ["knife", "stabbing", "blade", "machete"]):
        return "🔪"
    elif any(w in text_lower for w in ["gun", "shooting", "firearm", "shot"]):
        return "🔫"
    elif any(w in text_lower for w in ["court", "judge", "sentence", "prison", "trial"]):
        return "⚖️"
    return "🚨"

def detect_location(feed_url, text):
    for domain, loc in LOCATION_KEYWORDS.items():
        if domain in feed_url:
            return loc
    text_lower = text.lower()
    cities = ["manchester", "london", "glasgow", "edinburgh", "nottingham", "newcastle", "sunderland", "birmingham", "leicester", "leeds", "liverpool"]
    for city in cities:
        if city in text_lower:
            return city.capitalize()
    return "UK"

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    boilerplate = [r'^get the latest', r'^sign up to', r'^read more:', r'^© \d{4}']
    for pattern in boilerplate:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    return text

def scrape_full_article(url):
    try:
        headers = {"User-Agent": CONFIG["USER_AGENT"]}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup.select('script, style, header, footer, aside, .advertisement'):
                tag.decompose()
            body_container = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and 'body' in x)
            paragraphs = body_container.find_all('p') if body_container else soup.find_all('p')
            clean_paragraphs = [clean_text(p.get_text()) for p in paragraphs if len(p.get_text().strip()) > CONFIG["MIN_P_LENGTH"]]
            return "\n\n".join(clean_paragraphs)
    except Exception as e:
        print(f"Scraping error: {e}")
    return ""

def post_to_telegram(endpoint, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{endpoint}"
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()
    except Exception as e:
        print(f"Telegram API error: {e}")
        return None

def send_telegram_message(location, emoji, title, summary, body_text, link):
    clean_title = BeautifulSoup(title, 'html.parser').get_text()
    archive_link = link # fallback if archive fails

    # 1. Post full article text to the Archive Channel first (if configured)
    if TELEGRAM_ARCHIVE_CHAT_ID and body_text:
        chunks = [body_text[i:i+4000] for i in range(0, len(body_text), 4000)]
        first_archive_message_id = None
        
        for idx, chunk in enumerate(chunks):
            archive_payload = {
                "chat_id": TELEGRAM_ARCHIVE_CHAT_ID,
                "text": f"<b>{clean_title}</b>\n(Source: {link})\n\n{chunk}",
                "parse_mode": "HTML"
            }
            res = post_to_telegram("sendMessage", archive_payload)
            if res and res.get("ok"):
                if idx == 0:
                    first_archive_message_id = res["result"]["message_id"]
            time.sleep(0.3)
            
        # Generate deep link to the specific archive post if possible
        if first_archive_message_id and str(TELEGRAM_ARCHIVE_CHAT_ID).startswith("@"):
            channel_username = str(TELEGRAM_ARCHIVE_CHAT_ID).replace("@", "")
            archive_link = f"https://t.me/{channel_username}/{first_archive_message_id}"
        elif first_archive_message_id and str(TELEGRAM_ARCHIVE_CHAT_ID).startswith("-100"):
            # Clean up private channel ID format for t.me links (-100 removal)
            clean_id = str(TELEGRAM_ARCHIVE_CHAT_ID).replace("-100", "")
            archive_link = f"https://t.me/c/{clean_id}/{first_archive_message_id}"

    # 2. Post the clean, uncluttered card to your Main Channel with a button pointing to the full story
    main_message = (
        f"{emoji} <b>{location} Alert</b>\n\n"
        f"<b>{clean_title}</b>\n\n"
        f"<i>{clean_text(summary)}</i>"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": main_message,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📖 Read Full Story (Free)", "url": archive_link}]
            ]
        },
        "link_preview_options": {
            "url": link,
            "prefer_large_media": True,
            "show_above_text": True
        }
    }
    
    post_to_telegram("sendMessage", payload)

def run_bot():
    init_db()
    print("Bot started with clean feed + archive channel forwarding...")
    while True:
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    article_id = entry.id if 'id' in entry else entry.link
                    if not is_seen(article_id):
                        mark_as_seen(article_id)
                        title, link = entry.title, entry.link
                        summary = entry.summary if 'summary' in entry else ""
                        combined_text = (title + " " + summary).lower()
                        
                        if any(kw in combined_text for kw in KEYWORDS):
                            location = detect_location(feed_url, combined_text)
                            emoji = get_dynamic_emoji(combined_text)
                            scraped_body = scrape_full_article(link)
                            
                            send_telegram_message(location, emoji, title, summary, scraped_body, link)
                            time.sleep(1)
            except Exception as e:
                print(f"Feed error: {e}")
        time.sleep(CONFIG["SCAN_INTERVAL_SECONDS"])

if __name__ == "__main__":
    run_bot()
