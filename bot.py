import os
import time
import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import random
import re

# --- CONFIGURATION ---
CONFIG = {
    "DB_NAME": "uk_crime_bot.db",
    "SCAN_INTERVAL_SECONDS": 600,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "MIN_P_LENGTH": 60,
    "ORACLE_ENABLED": True,
    "MAX_RETRIES": 2,
    "SCRAPE_TIMEOUT": 18
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Two destinations
SHORT_CHAT_ID = "-1004494993483"          # UK crime news (group)
FULL_CHAT_ID  = "-1004311370107"          # UK Crime News full storys (channel)
FULL_CHANNEL_USERNAME = "UkCrimeNewsfullstorys"

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
    "https://www.leicestermercury.co.uk/news/?service=rss",
    "https://www.dailyrecord.co.uk/news/crime/rss.xml",
    "https://www.mirror.co.uk/news/uk-news/?service=rss",
    "https://www.walesonline.co.uk/news/?service=rss",
    "https://www.bristolpost.co.uk/news/?service=rss",
    "https://www.hulldailymail.co.uk/news/?service=rss",
    "https://www.devonlive.com/news/?service=rss",
    "https://www.cornwalllive.com/news/?service=rss",
    "https://www.examinerlive.co.uk/news/?service=rss",
    "https://www.cambridge-news.co.uk/news/?service=rss",
    "https://www.kentonline.co.uk/rss/"
]

KEYWORDS = [
    "court", "trial", "judge", "sentence", "prison", "hearing",
    "inquest", "crime", "jury", "offense", "offence",
    "robbery", "fight", "attack", "knife", "rape", "assault", "race",
    "hurt", "punch", "gun", "stabbing", "murder", "machete", "brawl",
    "gang", "shooting", "arrest", "charged", "investigation", "weapon",
    "thief", "burglary", "cops", "detectives", "tragedy", "tragic", "hotspot",
    "rightwing", "leftwing", "just in", "breaking news",
    "sex attack", "counter fit", "counterfeit", "police", "assaulted", "murdered",
    "stabbed", "shot", "raided", "raids", "wanted", "missing",
    "abducted", "kidnap", "kidnapped", "grooming", "exploitation",
    "fraud", "scam", "scammer", "theft", "stolen", "mugging",
    "mugged", "beaten", "beating", "homicide", "manslaughter",
    "domestic", "violence", "abuse", "stalking", "harassment",
    "threats", "threatening", "arson", "firebomb", "explosive",
    "bomb", "terror", "extremist", "riot", "disorder",
    "public order", "breach", "bail", "remanded", "sentenced",
    "jailed", "convicted", "guilty", "acquitted", "verdict"
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
    "bbci.co.uk": "National UK",
    "dailyrecord": "Scotland",
    "mirror": "National UK",
    "walesonline": "Wales",
    "bristolpost": "Bristol",
    "hulldailymail": "Hull",
    "devonlive": "Devon",
    "cornwalllive": "Cornwall",
    "examinerlive": "Yorkshire",
    "cambridge-news": "Cambridge",
    "kentonline": "Kent"
}

ORACLE_PREDICTIONS = [
    "The next hour carries a quiet weight. Something small is about to matter.",
    "Watch the edges of the hour — the real movement rarely happens in the centre.",
    "A decision made in the next 60 minutes will travel further than expected.",
    "The atmosphere is thinning. Pay attention to what feels slightly off.",
    "Someone will reveal more than they intended before the hour ends.",
    "What looks like delay is actually preparation. Stay ready.",
    "The next hour favours those who listen more than they speak.",
    "An old pattern is about to crack. Don’t force it — just notice.",
    "A message, a glance, or a silence will shift the tone of the next hour.",
    "Something you almost dismissed is the key to the coming hour.",
    "The air is charged. Move carefully but don’t stand still.",
    "A quiet opportunity will appear dressed as inconvenience.",
    "The next 60 minutes belong to the observant.",
    "Trust the strange feeling. It is accurate this time.",
    "What feels stuck is already beginning to move beneath the surface."
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
    elif any(w in text_lower for w in ["knife", "stabbing", "blade", "machete", "stabbed"]):
        return "🔪"
    elif any(w in text_lower for w in ["gun", "shooting", "firearm", "shot"]):
        return "🔫"
    elif any(w in text_lower for w in ["court", "judge", "sentence", "prison", "trial", "convicted", "jailed"]):
        return "⚖️"
    elif any(w in text_lower for w in ["fight", "brawl", "attack", "beaten"]):
        return "👊"
    elif any(w in text_lower for w in ["drug", "cocaine", "cannabis", "dealer"]):
        return "💊"
    elif any(w in text_lower for w in ["arson", "firebomb", "fire"]):
        return "🔥"
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
        "bradford", "coventry", "hull", "stoke", "cambridge", "kent",
        "devon", "cornwall", "wales"
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
    headers = {"User-Agent": CONFIG["USER_AGENT"]}
    
    for attempt in range(CONFIG["MAX_RETRIES"] + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=CONFIG["SCRAPE_TIMEOUT"]
            )
            
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup.select('script, style, header, footer, aside, .advertisement, .newsletter-signup, .social-embed, .ad, .ads'):
                tag.decompose()

            body_container = (
                soup.find('article') or 
                soup.find('main') or 
                soup.find('div', class_=lambda x: x and any(c in str(x).lower() for c in [
                    'article-body', 'story-body', 'content-body', 'post-content', 'article__body'
                ]))
            )
            
            if body_container:
                paragraphs = body_container.find_all('p')
            else:
                paragraphs = soup.find_all('p')
                
            clean_paragraphs = []
            for p in paragraphs:
                text = p.get_text().strip()
                if (len(text) > CONFIG["MIN_P_LENGTH"] and 
                    not text.startswith(('Credit:', 'PA Wire', 'SWNS', 'Image:', 'Getty', 'Related:'))):
                    clean_paragraphs.append(clean_text(text))
                    
            if clean_paragraphs:
                return "\n\n".join(clean_paragraphs)
            return ""
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < CONFIG["MAX_RETRIES"]:
                time.sleep(2 + attempt)
                continue
            return ""
        except Exception:
            return ""
    
    return ""

def send_telegram_with_retry(payload, max_retries=2):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, json=payload, timeout=15)
            data = response.json()
            
            if data.get("ok"):
                return data
            
            if data.get("error_code") == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 30)
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after + 2)
                continue
            
            print("Telegram error:", data)
            return data
        except Exception as e:
            print(f"Request error: {e}")
            time.sleep(3)
    return None

def send_dual_posts(location, emoji, title, summary, body_text, link):
    clean_title = BeautifulSoup(title, 'html.parser').get_text()
    
    # 1. Always post short card to the GROUP
    short_message = (
        f"{emoji} <b>[{location}] Breaking Alert</b>\n\n"
        f"<b>{clean_title}</b>\n\n"
        f"<i>{clean_text(summary)}</i>\n\n"
        f"📖 <a href=\"{link}\">Read full free story →</a>"
    )

    short_payload = {
        "chat_id": SHORT_CHAT_ID,
        "text": short_message,
        "parse_mode": "HTML",
        "link_preview_options": {
            "url": link,
            "prefer_large_media": True,
            "show_above_text": True
        }
    }
    
    short_data = send_telegram_with_retry(short_payload)
    if not short_data or not short_data.get("ok"):
        print("Failed to post short card")
        return
    
    short_message_id = short_data["result"]["message_id"]
    
    # 2. Only post full story if scraping succeeded
    if not body_text or len(body_text.strip()) < 80:
        print("Scraping failed – skipping full story channel")
        return
    
    chunks = [body_text[i:i+3900] for i in range(0, len(body_text), 3900)]
    full_message_ids = []
    
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            full_text = f"📖 <b>Full free story</b> (Part {i+1}/{len(chunks)}):\n\n{chunk}"
        else:
            full_text = f"📖 <b>Full free story:</b>\n\n{chunk}"
        
        full_payload = {
            "chat_id": FULL_CHAT_ID,
            "text": full_text,
            "parse_mode": "HTML"
        }
        
        time.sleep(1.3)
        full_data = send_telegram_with_retry(full_payload)
        
        if full_data and full_data.get("ok"):
            full_message_ids.append(full_data["result"]["message_id"])
    
    if not full_message_ids:
        print("Failed to post full story to channel")
        return
    
    # 3. Update short card with deep link
    full_msg_id = full_message_ids[0]
    deep_link = f"https://t.me/{FULL_CHANNEL_USERNAME}/{full_msg_id}"
    
    edited_message = (
        f"{emoji} <b>[{location}] Breaking Alert</b>\n\n"
        f"<b>{clean_title}</b>\n\n"
        f"<i>{clean_text(summary)}</i>\n\n"
        f"📖 <a href=\"{deep_link}\">Read full free story →</a>"
    )
    
    edit_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    edit_payload = {
        "chat_id": SHORT_CHAT_ID,
        "message_id": short_message_id,
        "text": edited_message,
        "parse_mode": "HTML",
        "link_preview_options": {
            "url": link,
            "prefer_large_media": True,
            "show_above_text": True
        }
    }
    
    try:
        time.sleep(0.8)
        requests.post(edit_url, json=edit_payload, timeout=10)
        print(f"Short card updated → {deep_link}")
    except Exception as e:
        print(f"Failed to edit short card: {e}")

def send_oracle():
    try:
        seed = random.randint(1, 999999)
        image_url = f"https://picsum.photos/seed/{seed}/800/600"
        prediction = random.choice(ORACLE_PREDICTIONS)
        now = datetime.now().strftime("%H:%M")
        
        caption = f"🔮 <b>Hourly Oracle — {now}</b>\n\n{prediction}"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": SHORT_CHAT_ID,
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
    print("Bot started → Clean dual posting (full story only when scrape succeeds)")
    
    while True:
        now = datetime.now()
        current_hour = now.hour
        
        if CONFIG["ORACLE_ENABLED"] and current_hour != last_oracle_hour and now.minute < 2:
            send_oracle()
            last_oracle_hour = current_hour
        
        print("Scanning feeds...")
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
                            
                            send_dual_posts(location, emoji, title, summary, scraped_body, link)
                            print(f"Posted [{location}]: {title}")
                            time.sleep(4)
            except Exception as e:
                print(f"Error on feed {feed_url}: {e}")
                
        time.sleep(CONFIG["SCAN_INTERVAL_SECONDS"])

if __name__ == "__main__":
    run_bot()
