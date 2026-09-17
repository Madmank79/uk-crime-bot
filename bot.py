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
import hashlib

# --- CONFIGURATION ---
CONFIG = {
    "DB_NAME": "uk_crime_bot.db",
    "SCAN_INTERVAL_SECONDS": 600,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "MIN_P_LENGTH": 60,
    "ORACLE_ENABLED": True,
    "MAX_RETRIES": 2
}

# Securely fetch secrets from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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

# --- KEYWORDS ---
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

VOLATILE_DOMAINS = [
    "manchestereveningnews.co.uk", "liverpoolecho.co.uk",
    "chroniclelive.co.uk", "birminghammail.co.uk",
    "leicestermercury.co.uk", "nottinghampost.com",
    "leeds-live.co.uk", "glasgowlive.co.uk"
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
    elif any(w in text_lower for w in ["court", "judge", "sentence", "prison", "trial", "convicted"]):
        return "⚖️"
    elif any(w in text_lower for w in ["fight", "brawl", "attack"]):
        return "👊"
    elif any(w in text_lower for w in ["drug", "cocaine", "cannabis", "dealer"]):
        return "💊"
    return "🚨"

def detect_location(feed_url, text):
    for domain, loc in LOCATION_KEYWORDS.items():
        if domain in feed_url:
            return loc
            
    text_lower = text.lower()
    cities = [
        "manchester", "london", "glasgow", "edinburgh", "nottingham", 
        "newcastle", "sunderland", "birmingham", "leicester", "leeds", 
        "liverpool", "cardiff", "belfast", "sheffield", "bristol", "york",
        "bradford", "coventry", "hull", "stoke"
    ]
    cities.sort(key=len, reverse=True)
    for city in cities:
        if city in text_lower:
            return city.capitalize()
    return "UK"

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    boilerplate = [
        r'^get the latest north east headlines direct to your inbox',
        r'^sign up to our newsletter',
        r'^read more:',
        r'^© \d{4}',
        r'click here to subscribe'
    ]
    for pattern in boilerplate:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    return text

def scrape_full_article(url):
    retries = 0
    while retries < CONFIG["MAX_RETRIES"]:
        try:
            headers = {"User-Agent": CONFIG["USER_AGENT"]}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for tag in soup.select('script, style, header, footer, aside, .advertisement, .newsletter-signup, .social-embed'):
                    tag.decompose()

                body_container = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and any(c in x for c in ['article-body', 'story-body', 'content-body', 'post-content']))
                
                if body_container:
                    paragraphs = body_container.find_all('p')
                else:
                    paragraphs = soup.find_all('p')
                    
                clean_paragraphs = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > CONFIG["MIN_P_LENGTH"] and not text.startswith(('Credit:', 'PA Wire', 'SWNS', 'Image:')):
                        clean_paragraphs.append(clean_text(text))
                        
                return "\n\n".join(clean_paragraphs)
        except Exception as e:
            print(f"Scraping error for {url}: {e}")
            retries += 1
            time.sleep(2)
    return ""

def send_telegram_message(location, emoji, title, summary, body_text, link, is_update=False):
    """Sends the alert header card and then posts the full article text cleanly right below it."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    header = f"[{location}] Update" if is_update else f"[{location}] Breaking Alert"
    clean_title = BeautifulSoup(title, 'html.parser').get_text()
    
    if not body_text or len(body_text.strip()) < 20:
        body_text = "Full text could not be automatically scraped from this site."

    # 1. Send the primary alert message with rich preview card
    main_message = (
        f"{emoji} <b>{header}</b>\n\n"
        f"<b>{clean_title}</b>\n\n"
        f"<i>{clean_text(summary)}</i>\n\n"
        f"🔗 <a href=\"{link}\">Original Source Link</a>"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": main_message,
        "parse_mode": "HTML",
        "link_preview_options": {
            "url": link,
            "prefer_large_media": True,
            "show_above_text": True
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        
        # 2. Automatically follow up with the full article text broken into chunks
        if body_text and len(body_text) > 20:
            chunks = [body_text[i:i+4000] for i in range(0, len(body_text), 4000)]
            
            for chunk in chunks:
                body_payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": f"📖 <b>Full Story:</b>\n\n{chunk}",
                    "parse_mode": "HTML"
                }
                requests.post(url, json=body_payload, timeout=15)
                time.sleep(0.5)
                
        return response.json()
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def send_oracle():
    try:
        seed = random.randint(1, 999999)
        image_url = f"https://picsum.photos/seed/{seed}/800/600"
        prediction = random.choice(ORACLE_PREDICTIONS)
        now = datetime.now().strftime("%H:%M")
        
        caption = f"🔮 <b>Hourly Oracle — {now}</b>\n\n{prediction}"
        
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
    last_oracle_hour = None
    init_db()
    print("Bot started with clean full-text delivery...")
    
    while True:
        now = datetime.now()
        current_hour = now.hour
        
        # === HOURLY ORACLE ===
        if CONFIG["ORACLE_ENABLED"] and current_hour != last_oracle_hour and now.minute < 2:
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
                            
                            send_telegram_message(location, emoji, title, summary, scraped_body, link)
                            print(f"Alert posted [{location}]: {title}")
                            time.sleep(1)
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        time.sleep(CONFIG["SCAN_INTERVAL_SECONDS"])

if __name__ == "__main__":
    run_bot()
