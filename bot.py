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
        r'^get the latest
