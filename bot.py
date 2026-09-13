import os
import time
import sqlite3
import feedparser
import requests
from bs4 import BeautifulSoup

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

# ---------------------------------------------------------
# VERIFIED DIRECT IMAGE LINKS FOR EACH REGION/CITY
# ---------------------------------------------------------
CUSTOM_LOCATION_IMAGES = {
    "London": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1200",
    "Manchester": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Manchester_Skyline_2018.jpg/1280px-Manchester_Skyline_2018.jpg",
    "Liverpool": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Albert_Dock_and_big_wheel%2C_Liverpool.jpg/1280px-Albert_Dock_and_big_wheel%2C_Liverpool.jpg",
    "Leeds": "https://images.unsplash.com/photo-1621570147414-236b2809fddf?w=1200",
    "Newcastle": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=1200",
    "Glasgow": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Glasgow_%28Unsplash%29.jpg/1280px-Glasgow_%28Unsplash%29.jpg",
    "Edinburgh": "https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb?w=1200",
    "Birmingham": "https://images.unsplash.com/photo-1593152167544-085dd8e342b0?w=1200",
    "Nottingham": "https://images.unsplash.com/photo-1618588507085-c79565432917?w=1200",
    "Sunderland": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Stadium_of_Light%2C_Sunderland_-_geograph.org.uk_-_5813943.jpg/1280px-Stadium_of_Light%2C_Sunderland_-_geograph.org.uk_-_5813943.jpg",
    "Leicester": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Leicester_Clock_Tower_wide_view.jpg/1280px-Leicester_Clock_Tower_wide_view.jpg",
    "UK Courts": "https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=1200",
    "National UK": "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1200",
    "UK": "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1200"
}

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

def send_custom_boxed_card(location, emoji, title, summary, body_text, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    chosen_image = CUSTOM_LOCATION_IMAGES.get(location, CUSTOM_LOCATION_IMAGES["UK"])
    
    caption = (
        f"{emoji} <b>UK NEWS FEED | {location} Alert</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{summary}\n\n"
        f"-----------------------------------\n"
        f"<b>Full Article:</b>\n{body_text}"
    )
    
    if len(caption) > 1020:
        caption = caption[:1000] + "...\n\n<i>[Truncated for length]</i>"

    reply_markup = {
        "inline_keyboard": [
            [{"text": "🌐 Open Original Web Article", "url": link}]
        ]
    }

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": chosen_image,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending telegram card: {e}")

def run_bot():
    init_db()
    print("Bot started with custom location picture mappings...")
    while True:
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
                            body_text = scraped_body if scraped_body else "<i>Full text could not be scraped.</i>"
                            
                            send_custom_boxed_card(location, emoji, title, summary, body_text, link)
                            print(f"Alert posted [{location}]: {title}")
                            time.sleep(1)
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        time.sleep(300)

if __name__ == "__main__":
    run_bot()
