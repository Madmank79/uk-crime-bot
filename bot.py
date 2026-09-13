
import os
import time
import re
import feedparser
import requests
from bs4 import BeautifulSoup

# Configuration from Railway Environment Variables
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

def scrape_article_data(url):
    """Scrapes the full text body and the main article image URL."""
    body_text = ""
    image_url = None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract main image (OpenGraph meta tag)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                image_url = og_image['content']
            
            # Extract body text
            body_container = soup.find('div', class_=lambda x: x and ('article-body' in x or 'story-body' in x or 'content-body' in x))
            if body_container:
                paragraphs = body_container.find_all('p')
            else:
                main_tag = soup.find('main') or soup.find('article') or soup
                paragraphs = main_tag.find_all('p')
                
            clean_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30]
            body_text = "\n\n".join(clean_paragraphs)
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
        
    return body_text, image_url

def send_telegram_post(location, title, summary, body_text, image_url, link):
    # 1. Send Photo + Title/Summary as caption (Picture at the very top)
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = (
        f"🚨 <b>{location} Alert</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"{summary}"
    )
    if len(caption) > 1024:  # Telegram caption limit
        caption = caption[:1020] + "..."

    photo_payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": image_url if image_url else "https://via.placeholder.com/600x400.png?text=News+Alert",
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(photo_url, data=photo_payload)
        time.sleep(0.5)
    except Exception as e:
        print(f"Error sending photo: {e}")

    # 2. Send Full Article Text right below it as a second message
    message_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    full_message = (
        f"<b>Full Article:</b>\n\n{body_text}\n\n"
        f"<a href='{link}'>Read original story</a>"
    )
    
    if len(full_message) > 4000:
        full_message = full_message[:3950] + "...\n\n<i>[Truncated]</i>"

    text_payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": full_message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(message_url, data=text_payload)
    except Exception as e:
        print(f"Error sending text body: {e}")

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
                            location = detect_location(feed_url, combined_text)
                            
                            # Scrape full body text and main image
                            body_text, image_url = scrape_article_data(link)
                            if not body_text:
                                body_text = "<i>Full text could not be scraped.</i>"
                            
                            send_telegram_post(location, title, summary, body_text, image_url, link)
                            print(f"Alert posted [{location}]: {title}")
                            time.sleep(1)
            except Exception as e:
                print(f"Error parsing feed {feed_url}: {e}")
                
        time.sleep(300)

if __name__ == "__main__":
    run_bot()
