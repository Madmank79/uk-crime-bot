import json

def send_telegram_inline_button(title, location, link, body_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Format a neat card for the timeline
    message = (
        f"🚨 <b>{location} Alert</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"<i>Tap the button below to view the full extracted story or source.</i>"
    )
    
    # Create an inline button payload
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📖 Read Full Story", "url": link}]
        ]
    }
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(reply_markup)
    }
    
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Error sending telegram message: {e}")

