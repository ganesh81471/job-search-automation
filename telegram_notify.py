"""
telegram_notify.py
--------------------
Sends a "scan is done, go apply" message to your phone via Telegram.

ONE-TIME SETUP (takes about 3 minutes):
1. Open Telegram, search for "BotFather" (the official bot for making bots).
2. Send it: /newbot
3. Follow the prompts — give your bot any name and a unique username ending in "bot".
4. BotFather replies with a token like: 123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   -> paste that into BOT_TOKEN below.
5. Now message YOUR new bot anything (e.g. "hi") from your own Telegram account —
   this is required once so the bot is allowed to message you back.
6. Run this file directly: python telegram_notify.py --get-chat-id
   It will print your chat_id — paste that into CHAT_ID below.
7. Run it again normally to send a test message: python telegram_notify.py

After setup, main.py calls send_notification() automatically at the end of
every scan — no further action needed.
"""

import sys
import requests

BOT_TOKEN = "7617737959:AAGjaWqhxkWWgo0qPxMo21vohd0_MdIXcPM"
CHAT_ID = "1741085033"     # <-- paste your chat_id here (see step 6 above)


def get_chat_id():
    """Run this once after messaging your bot, to find your chat_id."""
    if not BOT_TOKEN:
        print("Set BOT_TOKEN first (see the setup instructions at the top of this file).")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    resp = requests.get(url, timeout=10)
    data = resp.json()
    if not data.get("result"):
        print("No messages found yet. Send your bot a message on Telegram first, then re-run this.")
        return
    for update in data["result"]:
        chat = update.get("message", {}).get("chat", {})
        if chat:
            print(f"Found chat_id: {chat['id']}  (from user: {chat.get('first_name', '?')})")
    print("\nCopy the chat_id above into CHAT_ID at the top of telegram_notify.py.")


def send_notification(message: str):
    """Sends `message` to your phone. Fails silently with a printed warning
    rather than crashing the whole pipeline — a notification failing
    shouldn't take down a job scan that otherwise succeeded."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[notify] Telegram not configured yet (BOT_TOKEN/CHAT_ID empty) — skipping notification. "
              "See setup instructions at the top of telegram_notify.py.")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        resp.raise_for_status()
        print("[notify] Telegram message sent.")
        return True
    except Exception as e:
        print(f"[notify] Failed to send Telegram message: {e}")
        return False


if __name__ == "__main__":
    if "--get-chat-id" in sys.argv:
        get_chat_id()
    else:
        ok = send_notification("✅ Test message from your job search bot — setup works!")
        if not ok:
            print("\nIf this failed, double check BOT_TOKEN and CHAT_ID are both filled in above.")