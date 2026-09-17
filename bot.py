import os
import time
import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    "sex attack", "counter fit", "counterfeit", "police"
]

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

# === ORACLE SETTINGS ===
ORACLE_ENABLED = True
last_oracle_hour = None

ORACLE_PREDICTIONS = [
    "The next hour will bring movement in the shadows… watch the quiet ones.",
    "Something unexpected is already on its way. Stay sharp.",
    "A small decision made this hour will echo louder than you think.",
    "Keep your eyes open — the next 60 minutes belong to the unexpected.",
    "Old patterns are about to break. The next hour is a reset.",
    "Someone is about to reveal more than they intended.",
    "The atmosphere is shifting. Act before the window closes.",
    "A message, a glance, or a silence will change the tone of the next hour.",
    "What feels stuck is about to move. Be ready.",
    "The next hour favours those who stay calm under pressure.",
    "An opportunity will appear disguised as inconvenience.",
    "Trust the strange feeling. It’s accurate this time.",
    "The next 60 minutes will reward curiosity over caution.",
    "Something you almost ignored is the key to the next hour.",
    "A quiet hour that rearranges everything underneath."
]

def init_db():
    conn = sqlite3.connect("news_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seen_articles (
            article_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def is_seen(article_id):
    conn = sqlite3.connect("news_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_articles WHERE article_id = ?", (article_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_seen(article_id):
    conn = sqlite3.connect("news_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO seen_articles (article_id) VALUES (?)", (article_id,))
    conn.commit()
    conn.close()

def get_dynamic_emoji(text):
    text_lower = text.lower()
    if any(w in text_lower for w in ["court", "judge", "sentence", "prison", "hearing", "trial"]):
        return "⚖️"
    elif any(w in text_lower for w in ["knife", "stabbing", "weapon", "gun", "shooting", "machete"]):
        return "🔪"
    elif any(w in text_lower for w in ["murder", "tragedy", "tragic", "death", "killed"]):
        return "⚠️"
    return "🚨"

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

def scrape_full_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            body_container = soup.find('div', class_=lambda x: x and ('article-body' in x or 'story-body' in x or 'content-body' in x))
            
            if body_container:
                paragraphs = body_container.find_all('p')
            else:
                main_tag = soup.find('main') or soup.find('article') or soup
                paragraphs = main_tag.find_all('p')
                
            clean_paragraphs = []
            boilerplate_phrases = ["preferred source", "google news", "sign up", "newsletter", "cookie policy"]
            
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 30 and not any(bp in text.lower() for bp in boilerplate_phrases):
                    clean_paragraphs.append(text)
                    
            return "\n\n".join(clean_paragraphs)
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
    return ""

def send_telegram_single_message(location, emoji, title, summary, body_text, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if not body_text or body_text.strip() == "":
        body_text = "Full text could not be scraped."
    
    # Very short preview → keeps the grey block small
    preview = body_text[:160].strip()
    if len(body_text) > 160:
        preview += "..."

    message = (
        f"{emoji} <b>{location} Alert</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{summary}\n\n"
        f"📖 <span class=\"tg-spoiler\">{preview}</span>\n\n"
        f"🔗 <a href=\"{link}\">Read full story</a>"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "link_preview_options": {
            "url": link,
            "prefer_large_media": True,
            "show_above_text": True
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        return response.json()
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def send_oracle():
    """Post a random picture + prediction every hour on the hour"""
    try:
        seed = random.randint(1, 999999)
        image_url = f"https://picsum.photos/seed/{seed}/800/600"
        
        prediction = random.choice(ORACLE_PREDICTIONS)
        now = datetime.now().strftime("%H:%M")
        
        caption = (
            f"🔮 <b>Hourly Oracle — {now}</b>\n\n"
            f"{prediction}"
        )
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print(f"Oracle posted at {now}")
        else:
            print(f"Oracle failed: {response.text}")
            
    except Exception as e:
        print(f"Oracle error: {e}")

def run_bot():
    global last_oracle_hour
    init_db()
    print("Bot started with small spoiler + Read full story link...")
    
    while True:
        now = datetime.now()
        current_hour = now.hour
        
        # === HOURLY ORACLE ===
        if ORACLE_ENABLED and current_hour != last_oracle_hour and now.minute < 2:
            send_oracle()
            last_oracle_hour = current_hour
        
        # === NORMAL CRIME SCAN ===
        print("Scanning feeds for new updates...")
        for feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    article_id = entry.id if 'id' in entry else entry.link
                    title = entry.title
                    link = entry.link

                    if not is_seen(article_id):
                        mark_as_seen(article_id)
                        
                        summary = entry.summary if 'summary' in entry else ""
                        combined_text = (title + " " + summary).lower()
                        
                        if any(kw in combined_text for kw in KEYWORDS):
                            location = detect_location(feed_url, combined_text)
                            emoji = get_dynamic_emoji(combined_text)
                            
                            scraped_body = scrape_full_article(link)
                            body_text = scraped_body if scraped_body else "Full text could not be scraped."
                            
                            send_telegram_single_message(location, emoji, title, summary, body_text, link)
                            print(f"Alert posted [{location}]: {title}")
                            time.sleep(1)
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        time.sleep(300)   # every 5 minutes

if __name__ == "__main__":
    run_bot()
