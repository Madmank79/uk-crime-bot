import time
import requests
from bs4 import BeautifulSoup

# Configuration (Replace these placeholders with your actual tokens/IDs)
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

def clean_text(text):
    """Helper function to clean up text content."""
    if not text:
        return ""
    return BeautifulSoup(text, 'html.parser').get_text()

def send_telegram_message(location, emoji, title, summary, body_text, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    clean_title = clean_text(title)
    
    main_message = (
        f"{emoji} <b>[{location}] Breaking Alert</b>\n\n"
        f"<b>{clean_title}</b>\n\n"
        f"<i>{clean_text(summary)}</i>\n\n"
        f"🔗 <a href=\"{link}\">Original Source</a>"
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
        data = response.json()
        
        # Handle rate limit (Error 429)
        if not data.get("ok"):
            if data.get("error_code") == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 30)
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after + 2)
                # Retry once after waiting
                response = requests.post(url, json=payload, timeout=15)
                data = response.json()
            
            if not data.get("ok"):
                print("Failed to send main message:", data)
                return
        
        message_id = data["result"]["message_id"]
        
        # Full free story as reply (with extra delay to prevent flooding)
        if body_text and len(body_text.strip()) > 40:
            chunks = [body_text[i:i+3900] for i in range(0, len(body_text), 3900)]
            
            for i, chunk in enumerate(chunks):
                if len(chunks) > 1:
                    reply_text = f"📖 <b>Full free story</b> (Part {i+1}/{len(chunks)}):\n\n{chunk}"
                else:
                    reply_text = f"📖 <b>Full free story:</b>\n\n{chunk}"
                
                reply_payload = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": reply_text,
                    "parse_mode": "HTML",
                    "reply_to_message_id": message_id
                }
                
                # Small delay between chunks
                time.sleep(1.5)
                requests.post(url, json=reply_payload, timeout=15)
                
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def main_loop():
    """Example main loop demonstrating how to process your stories/alerts."""
    # Dummy data list to simulate incoming stories
    stories = [
        {
            "location": "Global",
            "emoji": "🚨",
            "title": "Example Alert Title",
            "summary": "This is a brief summary of the breaking story.",
            "body_text": "This is the full text of the story. If it is very long, it will automatically get chunked into smaller pieces so it doesn't break Telegram's message character limits.",
            "link": "https://example.com"
        }
    ]

    for story in stories:
        print(f"Posting story: {story['title']}")
        send_telegram_message(
            location=story["location"],
            emoji=story["emoji"],
            title=story["title"],
            summary=story["summary"],
            body_text=story["body_text"],
            link=story["link"]
        )
        
        # Slower delay between posting individual stories to avoid rate limits
        time.sleep(4)

if __name__ == "__main__":
    main_loop()
