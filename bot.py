
import os
import time
import json
import logging
import asyncio
from dotenv import load_dotenv
import feedparser
from telegram import Bot

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://www.manchestereveningnews.co.uk/news/?service=rss",
    "https://www.leeds-live.co.uk/news/?service=rss",
    "https://www.liverpoolecho.co.uk/news/?service=rss",
    "https://www.birminghammail.co.uk/news/?service=rss",
    "https://www.mylondon.news/news/?service=rss",
    "https://www.blackpoolgazette.co.uk/rss",
    "https://www.lancs.live/news/?service=rss",
    "https://www.glasgowlive.co.uk/news/?service=rss",
    "https://www.edinburghlive.co.uk/news/?service=rss",
    "https://www.leicestermercury.co.uk/news/?service=rss",
    "https://www.chroniclelive.co.uk/news/?service=rss",
    "https://www.nottinghampost.com/news/?service=rss",
    "https://www.kentlive.news/news/?service=rss",
    "https://feeds.bbci.co.uk/news/uk/rss.xml",
    "https://siss.gmp.police.uk/news.xml"
]

# Map feed URLs to default location headers
FEED_LOCATIONS = {
    "manchestereveningnews.co.uk": "MANCHESTER",
    "leeds-live.co.uk": "LEEDS",
    "liverpoolecho.co.uk": "LIVERPOOL",
    "birminghammail.co.uk": "BIRMINGHAM",
    "mylondon.news": "LONDON",
    "blackpoolgazette.co.uk": "BLACKPOOL",
    "lancs.live": "LANCASHIRE",
    "glasgowlive.co.uk": "GLASGOW",
    "edinburghlive.co.uk": "EDINBURGH",
    "leicestermercury.co.uk": "LEICESTER",
    "chroniclelive.co.uk": "NEWCASTLE",
    "nottinghampost.com": "NOTTINGHAM",
    "kentlive.news": "KENT",
    "bbci.co.uk": "UK",
    "siss.gmp.police.uk": "GREATER MANCHESTER POLICE"
}

# Specific neighborhoods/towns to detect inside text for precise headers
SPECIFIC_AREAS = [
    "audenshaw", "denton", "gorton", "levenshulme", 
    "moss side", "salford", "wythenshawe", "stockport", 
    "sunderland", "morecambe", "rochdale"
]

CRIME_KEYWORDS = [
    "police", "arrest", "murder", "court", "jail", "prison", 
    "officers", "assault", "investigation", "stabbing", "gun", 
    "drugs", "search warrant", "appeal", "robbery", "cops", 
    "detectives", "shooting", "knife", "brawl", "incident", "collision",
    "fight", "stabbed", "race", "migrants", "rape"
]

SEEN_FILE = "seen_combined_crime.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r") as f:
                return set(json.load(f))
        except:
            pass
    return set()

def save_seen(seen):
    try:
        with open(SEEN_FILE, "w") as f:
            json.dump(list(seen), f)
    except:
        pass

def is_valid_crime_story(title, summary=""):
    text = f"{title} {summary}".lower()
    return any(keyword in text for keyword in CRIME_KEYWORDS)

def get_post_location(feed_url, title, summary=""):
    text = f"{title} {summary}".lower()
    
    # Check if any specific hyper-local area is mentioned in the post content
    for area in SPECIFIC_AREAS:
        if area in text:
            return area.upper()
            
    # Otherwise fallback to the primary region mapped from the feed URL
    for domain, location in FEED_LOCATIONS.items():
        if domain in feed_url:
            return location
            
    return "UK"

async def initialize_feeds(seen_articles):
    if len(seen_articles) > 0:
        return
    logger.info("First run detected: Caching existing articles silently...")
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                article_id = entry.get("id") or entry.get("link")
                if article_id:
                    seen_articles.add(article_id)
        except Exception as e:
            logger.error(f"Error initializing feed {feed_url}: {e}")
    save_seen(seen_articles)
    logger.info(f"Initialization complete. Cached {len(seen_articles)} existing articles.")

async def check_feeds(bot, seen_articles):
    new_count = 0
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                article_id = entry.get("id") or entry.get("link")
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                
                if article_id and article_id not in seen_articles:
                    seen_articles.add(article_id)
                    
                    if is_valid_crime_story(title, summary):
                        location_tag = get_post_location(feed_url, title, summary)
                        message = f"🚨 *{location_tag} CRIME ALERT*\n\n*{title}*\n\n{link}"
                        
                        try:
                            await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
                            logger.info(f"Sent alert [{location_tag}]: {title}")
                            new_count += 1
                            await asyncio.sleep(4)
                        except Exception as telegram_error:
                            logger.error(f"Telegram error sending message: {telegram_error}")
                            await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"Error checking feed {feed_url}: {e}")
            
    save_seen(seen_articles)
    return new_count

async def main():
    if not TOKEN or not CHAT_ID:
        logger.error("Missing token or chat ID.")
        return
        
    bot = Bot(token=TOKEN)
    seen_articles = load_seen()
    
    await initialize_feeds(seen_articles)
    
    logger.info("Location-Tagged UK Crime Bot is running...")
    
    while True:
        count = await check_feeds(bot, seen_articles)
        if count == 0:
            try:
                await bot.send_message(chat_id=CHAT_ID, text="🔄 Master Scan: No new crime reports at this time.")
            except:
                pass
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())
