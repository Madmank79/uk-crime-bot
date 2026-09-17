def send_telegram_single_message(location, emoji, title, summary, body_text, link):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    if not body_text or body_text.strip() == "":
        body_text = "Full text could not be scraped."
    
    # Very short preview so the grey block stays small
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
